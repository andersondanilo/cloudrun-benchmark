use poem::{
    error::InternalServerError, get, handler, http::StatusCode, listener::TcpListener, web::Data,
    EndpointExt, Response, Result, Route, Server,
};
use redis::{aio::ConnectionManager, AsyncCommands};

const KEY: &str = "benchmark:data";

#[handler]
async fn get_data(Data(redis): Data<&ConnectionManager>) -> Result<Response> {
    let mut conn = redis.clone();
    let body: Option<String> = conn.get(KEY).await.map_err(InternalServerError)?;
    Ok(match body {
        Some(b) => Response::builder().content_type("application/json").body(b),
        None => Response::builder()
            .status(StatusCode::NOT_FOUND)
            .content_type("application/json")
            .body(r#"{"error":"key not set, run scripts/setup.py"}"#),
    })
}

#[tokio::main]
async fn main() -> std::io::Result<()> {
    let port = std::env::var("PORT").unwrap_or_else(|_| "8080".into());
    let redis_url = std::env::var("REDIS_URL").unwrap_or_else(|_| "redis://localhost:6379".into());
    let client = redis::Client::open(redis_url).expect("invalid REDIS_URL");
    let conn = ConnectionManager::new(client).await.expect("redis connect");

    let app = Route::new().at("/data", get(get_data)).data(conn);
    Server::new(TcpListener::bind(format!("0.0.0.0:{port}")))
        .run(app)
        .await
}
