package main

import "testing"

func testVersion(t *testing.T) {
	if Version() != version {
		t.Error("this test should never fail")
	}
}
