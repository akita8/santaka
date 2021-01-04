package main

import (
	"context"
	"io/ioutil"
	"log"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/akita8/santaka/backend/pb"
	"github.com/golang/protobuf/ptypes/empty"
	"google.golang.org/grpc"
)

type pingerTestClient struct{}

func (ptc *pingerTestClient) Ping(ctx context.Context, in *empty.Empty, opts ...grpc.CallOption) (*empty.Empty, error) {
	return &empty.Empty{}, nil
}

func newPingerTestClient(cc grpc.ClientConnInterface) pb.PingerClient {
	return &pingerTestClient{}
}

func TestHandlePingSuccess(t *testing.T) {
	srv := newAPI(http.NewServeMux(), &grpc.ClientConn{}, log.New(ioutil.Discard, "", log.LstdFlags))
	srv.router.HandleFunc("/ping", srv.handlePing(newPingerTestClient))
	req := httptest.NewRequest("GET", "/ping", nil)
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", w.Code)
	}
	responseBody := w.Body.String()
	if responseBody != pingResponseBody {
		t.Errorf("expected %s, got %s", pingResponseBody, responseBody)
	}
}

func TestHandlePingError(t *testing.T) {
	conn, err := grpc.Dial("127.0.0.1:66666", grpc.WithInsecure())
	if err != nil {
		t.Fatalf("failed to create grpc connection %v", err)
	}
	srv := newAPI(http.NewServeMux(), conn, log.New(ioutil.Discard, "", log.LstdFlags))
	srv.routes()
	req := httptest.NewRequest("GET", "/ping", nil)
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)
	if w.Code != http.StatusInternalServerError {
		t.Errorf("got %d, expected 500, ", w.Code)
	}
}
