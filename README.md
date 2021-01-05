# Santaka


## Code generation

In order to generate protobuf and grpc code install the packages dependencies, the protoc compiler and run this commands.


### Backend

```bash
cd backend
protoc --proto_path=.. --go_out=pb --go-grpc_out=pb --go-grpc_opt=paths=source_relative --go_opt=paths=source_relative ../santaka.proto
```


### Engine
After editing santaka.proto file run the following command (from the `engine` directory) to generate protobuf and grpc files: 
```bash
poetry run generate
```

In order to call the engine services you can use [gpcurl](https://github.com/fullstorydev/grpcurl)
(replace service and method with the service name and the method name you want to call, and place the correct request body).

On Windows:

```powershell
.\grpcurl.exe -d '{}' -plaintext -import-path C:\path\to\santaka\folder -proto santaka.proto localhost:50051 santaka.service/method
```

On Linux:
```bash
grpcurl -d '{}' -plaintext -import-path /path/to/santaka/folder -proto santaka.proto localhost:50051 santaka.service/method
```