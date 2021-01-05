package main

import (
	"net/http"

	"github.com/akita8/santaka/backend/pb"
	"google.golang.org/grpc"
	"google.golang.org/protobuf/types/known/emptypb"
)

const pingResponseBody = "pong\n"

type pingerConstructor func(cc grpc.ClientConnInterface) pb.PingerClient

func (a *api) handlePing(pc pingerConstructor) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		c := pc(a.engineConn)
		_, err := c.Ping(r.Context(), &emptypb.Empty{})
		if err != nil {
			a.logger.Printf("failed to ping santaka engine: %v", err)
			w.WriteHeader(http.StatusInternalServerError)
			return
		}
		w.Write([]byte(pingResponseBody))
	}
}

func (a *api) routes() {
	a.router.HandleFunc("/ping", a.handlePing(pb.NewPingerClient))
}
