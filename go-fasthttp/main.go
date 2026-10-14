package main

import (
	"context"
	"log"
	"math/rand/v2"
	"os"
	"strconv"
	"time"

	"github.com/fasthttp/router"
	"github.com/redis/rueidis"
	"github.com/valyala/fasthttp"
)

const (
	keyPrefix = "benchmark:data"
	count     = 20 // documents stored by scripts/setup.py as benchmark:data:0 .. :19
)

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	opt, err := rueidis.ParseURL(getenv("REDIS_URL", "redis://localhost:6379"))
	if err != nil {
		log.Fatalf("invalid REDIS_URL: %v", err)
	}
	// Redis may still be booting (e.g. a freshly created VM), so retry instead of exiting.
	var client rueidis.Client
	for {
		client, err = rueidis.NewClient(opt)
		if err == nil {
			break
		}
		log.Printf("redis connect: %v (retrying in 2s)", err)
		time.Sleep(2 * time.Second)
	}
	defer client.Close()

	r := router.New()
	r.GET("/data", func(ctx *fasthttp.RequestCtx) {
		key := keyPrefix + ":" + strconv.Itoa(rand.IntN(count))
		data, err := client.Do(context.Background(), client.B().Get().Key(key).Build()).AsBytes()
		if rueidis.IsRedisNil(err) {
			ctx.SetStatusCode(fasthttp.StatusNotFound)
			ctx.SetContentType("application/json")
			ctx.SetBodyString(`{"error":"key not set, run scripts/setup.py"}`)
			return
		}
		if err != nil {
			ctx.Error(err.Error(), fasthttp.StatusInternalServerError)
			return
		}
		ctx.SetContentType("application/json")
		ctx.SetBody(data)
	})

	addr := ":" + getenv("PORT", "8080")
	log.Fatal(fasthttp.ListenAndServe(addr, r.Handler))
}
