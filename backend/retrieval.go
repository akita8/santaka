package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"
)

var errFailedValidation = errors.New("failed validation")
var errFailedRetrieval = errors.New("failed data retrieval")

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

type yahooChart struct {
	client *http.Client
	url    string
}

func (c *yahooChart) retrieve(symbol string) (d liveStockData, err error) {
	resp, err := c.client.Get(fmt.Sprintf("%s/%s", c.url, strings.ToUpper(symbol)))
	if err != nil {
		return d, fmt.Errorf("failed get request to yahoo finance api: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return d, fmt.Errorf("%w: yahoo finance api http response status is not 200: %d", errFailedRetrieval, resp.StatusCode)
	}

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

type liveBondData struct {
	currency       string
	lastPrice      float64
	nextCouponRate float64
	maturity       time.Time
}

type borsaItaliana struct {
	client *http.Client
	url    string
}