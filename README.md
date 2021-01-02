# Santaka


## Code generation

In order to generate protobuf and grpc code install the packages dependencies, the protoc compiler and run this commands.


### Backend

```bash
cd backend
protoc --proto_path=.. --go_out=pb --go-grpc_out=pb --go-grpc_opt=paths=source_relative --go_opt=paths=source_relative ../santaka.proto
```


### Engine
After editing santaka.proto file run the following code to generate protobuf interfaces in engine directory: 
```bash
poetry run python -m grpc_tools.protoc -I.. --python_out=engine --grpc_python_out=engine ../santaka.proto
```

Warning: after compiling santaka.proto change import path in santaka_pb2_grpc from `import santaka_pb2 as santaka__pb2` to `import engine.santaka_pb2 as santaka__pb2`.

In order to call the engine services you can use [gpcurl]().

On Windows:

```powershell
# obviosuly replace service and method with the service name and the method name you want to call
.\grpcurl.exe -d '{}' -plaintext -import-path C:\path\to\santaka\folder -proto santaka.proto localhost:50051 santaka.service/method
```

On Linux:
```bash
# obviosuly replace service and method with the service name and the method name you want to call
grpcurl -d '{}' -plaintext -import-path /path/to/santaka/folder -proto santaka.proto localhost:50051 santaka.service/method
```