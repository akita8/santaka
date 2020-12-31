package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"google.golang.org/grpc"
)

const version = "0.1.0"

var (
	host          = flag.String("host", "127.0.0.1", "the host the server binds to")
	port          = flag.Int("port", 8000, "the port the server binds to")
	engineAddress = flag.String("engine-address", "127.0.0.1:50051", "the address of the engine grpc server")
)

// Version returns santaka/backend version
func Version() string {
	return version
}

type api struct {
	router     *http.ServeMux
	engineConn *grpc.ClientConn
}

func (a *api) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	a.router.ServeHTTP(w, r)
}

func newAPI(m *http.ServeMux, ec *grpc.ClientConn) *api {
	return &api{
		router:     m,
		engineConn: ec,
	}
}

func main() {
	flag.Parse()

	conn, err := grpc.Dial(*engineAddress, grpc.WithInsecure())
	if err != nil {
		log.Fatalf("failed to dial a connection to rpc server: %v", err)
	}
	defer conn.Close()

	a := newAPI(http.NewServeMux(), conn)
	a.routes()

	address := fmt.Sprintf("%s:%d", *host, *port)

	srv := http.Server{
		Addr:    address,
		Handler: a,
	}

	log.Printf("santaka backend server listening on %s", address)

	idleConnectionsClosed := make(chan struct{})
	go func() {
		sigint := make(chan os.Signal, 1)
		signal.Notify(sigint, syscall.SIGINT, syscall.SIGTERM, syscall.SIGKILL)
		<-sigint
		// We received an interrupt signal, shut down.
		if err := srv.Shutdown(context.Background()); err != nil {
			log.Fatalf("Shutdown, error while closing connections: %v", err)
		}
		close(idleConnectionsClosed)
	}()

	if err := srv.ListenAndServe(); err != http.ErrServerClosed {
		log.Fatalf("Shutdown, error starting or closing http server: %v", err)
	}
	log.Printf("Shutdown complete")

	<-idleConnectionsClosed

}
