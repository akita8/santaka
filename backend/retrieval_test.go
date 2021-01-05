package main

import (
	"errors"
	"fmt"
	"io/ioutil"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestYahooChartRetrieveErrors(t *testing.T) {
	tests := []struct {
		name               string
		responseStatusCode int
		expectedErr        error
		expected           liveStockData
	}{
		{"yahoo_chart_error_empty", 400, errFailedRetrieval, liveStockData{}},
		{"yahoo_chart_error_incomplete", 200, errFailedValidation, liveStockData{}},
		{"yahoo_chart_success", 200, nil, liveStockData{"USD", 132.69}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f, err := ioutil.ReadFile(fmt.Sprintf("testdata/%s.json", tt.name))
			if err != nil {
				t.Fatalf("failed to open yahoo chart test response: %s", err)
			}

			ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.WriteHeader(tt.responseStatusCode)
				w.Write(f)
			}))
			defer ts.Close()

			c := &yahooChart{
				client: ts.Client(),
				url:    ts.URL,
			}

			data, err := c.retrieve("aapl")
			if err != nil && !errors.Is(err, tt.expectedErr) {
				t.Errorf("expected error that wraps [%v], got [%v]", tt.expectedErr, err)
			}
			if data.lastPrice != tt.expected.lastPrice {
				t.Errorf("expected [%f], got [%f]", tt.expected.lastPrice, data.lastPrice)
			}
			if data.currency != tt.expected.currency {
				t.Errorf("expected [%s], got [%s]", tt.expected.currency, data.currency)
			}
		})
	}
}
