package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
)

var errFailedValidation = errors.New("failed validation")

type liveStockData struct {
	currency  string
	lastPrice float64
}

type yahooFinanceResponse struct {
	Chart struct {
		Result []struct {
			Meta struct {
				Currency           *string  `json:"currency"`
				RegularMarketPrice *float64 `json:"regularMarketPrice"`
			} `json:"meta"`
		} `json:"result"`
	} `json:"chart"`
}

func (r *yahooFinanceResponse) currency() string {
	return *r.Chart.Result[0].Meta.Currency
}

func (r *yahooFinanceResponse) lastPrice() float64 {
	return *r.Chart.Result[0].Meta.RegularMarketPrice
}

func (r *yahooFinanceResponse) data() (d liveStockData, err error) {
	if r.Chart.Result == nil || len(r.Chart.Result) == 0 {
		return d, fmt.Errorf("%w: missing required result array", errFailedValidation)
	}
	if r.Chart.Result[0].Meta.Currency == nil {
		return d, fmt.Errorf("%w: missing required currency field", errFailedValidation)
	}
	if r.Chart.Result[0].Meta.RegularMarketPrice == nil {
		return d, fmt.Errorf("%w: missing required regularMarketPrice field", errFailedValidation)
	}
	d.currency = r.currency()
	d.lastPrice = r.lastPrice()
	return d, err
}

type stockRetriever interface {
	retrieve(symbol string) (liveStockData, error)
}

type yahooChart struct {
	endpoint string
}

func (c *yahooChart) retrieve(symbol string) (d liveStockData, err error) {
	resp, err := http.Get(fmt.Sprintf("%s%s", c.endpoint, symbol))
	if err != nil {
		return d, fmt.Errorf("failed getting yahoo finance api: %w", err)
	}
	defer resp.Body.Close()

	r := new(yahooFinanceResponse)
	dec := json.NewDecoder(resp.Body)
	err = dec.Decode(r)
	if err != nil {
		return d, fmt.Errorf("failed parsing yahoo finance api json response: %w", err)
	}

	d, err = r.data()
	if err != nil {
		return d, fmt.Errorf("failed obtaining live stock data from yahoo finance api response: %w", err)
	}

	return d, err
}
