package main

import "testing"

func TestVersion(t *testing.T) {
	if Version() != version {
		t.Error("this test should never fail")
	}
}
