package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"golang.org/x/net/html"
)

const (
	currencyFieldName       string = "Trading currency"
	lastPriceFieldName      string = "Close price"
	nextCouponRateFieldName string = "Current coupon rate"
	maturityFieldName       string = "Maturity"
	maturityLayout          string = "01/02/2006"
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
}

func (c *yahooChart) retrieve(url string) (d liveStockData, err error) {
	resp, err := c.client.Get(url)
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
	url            string
}

func (d *liveBondData) isValidField(name string) bool {
	switch strings.TrimSpace(name) {
	case currencyFieldName:
		fallthrough
	case lastPriceFieldName:
		fallthrough
	case nextCouponRateFieldName:
		fallthrough
	case maturityFieldName:
		return true
	}
	return false
}

func (d *liveBondData) field(name, value string) error {
	value = strings.TrimSpace(value)
	switch strings.TrimSpace(name) {
	case currencyFieldName:
		d.currency = value
	case lastPriceFieldName:
		n, err := strconv.ParseFloat(value, 64)
		if err != nil {
			return err
		}
		d.lastPrice = n
	case nextCouponRateFieldName:
		n, err := strconv.ParseFloat(value, 64)
		if err != nil {
			return err
		}
		d.nextCouponRate = n
	case maturityFieldName:
		m, err := time.Parse(maturityLayout, value)
		if err != nil {
			return err
		}
		d.maturity = m
	}
	return nil
}

type borsaItaliana struct {
	client *http.Client

	nextFieldName string
	extracted     *liveBondData
}

func (b *borsaItaliana) extract(n *html.Node) {
	if n.Type == html.TextNode && b.extracted.isValidField(n.Data) {
		b.nextFieldName = n.Data
	} else if n.Type == html.ElementNode && n.Data == "span" && b.nextFieldName != "" {
		for _, attr := range n.Attr {
			if attr.Key == "class" && strings.HasPrefix(attr.Val, "t-text -right") {
				b.extracted.field(b.nextFieldName, n.FirstChild.Data)
				b.nextFieldName = ""
				break
			}
		}
	}
	for c := n.FirstChild; c != nil; c = c.NextSibling {
		b.extract(c)
	}
}

func (b *borsaItaliana) retrieve(url string) (d liveBondData, err error) {
	resp, err := b.client.Get(url)
	if err != nil {
		return d, fmt.Errorf("failed get request to borsa italiana: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return d, fmt.Errorf("%w: borsa italiana http response status is not 200: %d", errFailedRetrieval, resp.StatusCode)
	}

	parsed, err := html.Parse(resp.Body)
	if err != nil {
		return d, err
	}

	b.extracted = &d
	b.extract(parsed)
	if d.currency == "" || d.lastPrice == 0 {
		return d, errFailedRetrieval
	}
	d.url = resp.Request.URL.String()
	return d, nil
}
