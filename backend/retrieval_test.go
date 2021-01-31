package main

import (
	"errors"
	"fmt"
	"io/ioutil"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestYahooChartRetrieve(t *testing.T) {
	tests := []struct {
		name               string
		responseStatusCode int
		expectedErr        error
		expected           liveStockData
	}{
		{"yahoo_chart_error_empty", 400, errFailedRetrieval, liveStockData{}},
		{"yahoo_chart_error_incomplete", 200, errFailedRetrieval, liveStockData{}},
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
			}

			data, err := c.retrieve(ts.URL)
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

func TestBorsaItalianaRetrieve(t *testing.T) {
	tests := []struct {
		name               string
		responseStatusCode int
		expectedErr        error
		expected           liveBondData
	}{
		{"borsaitaliana_search_success", 200, nil, liveBondData{currency: "GBP", lastPrice: 108.74}},
		{"borsaitaliana_complete_success", 200, nil, liveBondData{
			currency:       "GBP",
			lastPrice:      108.71,
			nextCouponRate: 1.5,
			maturity:       time.Date(2026, time.Month(7), 22, 0, 0, 0, 0, time.UTC),
		}},
		{"borsaitaliana_error_incomplete", 200, errFailedRetrieval, liveBondData{}},
		{"borsaitaliana_error_incomplete", 400, errFailedRetrieval, liveBondData{}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f, err := ioutil.ReadFile(fmt.Sprintf("testdata/%s.html", tt.name))
			if err != nil {
				t.Fatalf("failed to open borsa italiana test response: %s", err)
			}

			ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.WriteHeader(tt.responseStatusCode)
				w.Write(f)
			}))
			defer ts.Close()

			c := &borsaItaliana{
				client: ts.Client(),
			}

			data, err := c.retrieve(ts.URL)
			if tt.expectedErr != nil && !errors.Is(err, tt.expectedErr) {
				t.Errorf("expected error that wraps [%v], got [%v]", tt.expectedErr, err)
			}
			if err == nil {
				tt.expected.url = ts.URL
			}
			if data != tt.expected {
				t.Errorf("expected [%+v], got [%+v]", tt.expected, data)
			}
		})
	}
}
