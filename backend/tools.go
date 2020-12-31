// +build tools

package main

// Temporary fix for unreleased grpc plugin issue
// (https://github.com/grpc/grpc-go/pull/3453#issuecomment-634945192).
// This file is never included in the binary (thanks to th build tag)
// but the plugin is downloaded when building the first time
// and can be used by protoc to generate grpc stubs.

import (
	_ "google.golang.org/grpc/cmd/protoc-gen-go-grpc"
)
