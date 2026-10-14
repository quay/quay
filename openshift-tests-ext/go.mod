module github.com/quay/quay/openshift-tests-ext

go 1.23.0

require (
	github.com/openshift-eng/openshift-tests-extension v0.0.0-20260831105930-c81d84cb88a7
	github.com/spf13/cobra v1.8.1
)

require (
	github.com/antlr/antlr4/runtime/Go/antlr/v4 v4.0.0-20230305170008-8188dc5388df // indirect
	github.com/google/cel-go v0.17.8 // indirect
	github.com/inconshreveable/mousetrap v1.1.0 // indirect
	github.com/spf13/pflag v1.0.5 // indirect
	github.com/stoewer/go-strcase v1.2.0 // indirect
	golang.org/x/exp v0.0.0-20230515195305-f3d0a9c9a5cc // indirect
	golang.org/x/text v0.19.0 // indirect
	google.golang.org/genproto/googleapis/api v0.0.0-20240528184218-531527333157 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20240924160255-9d4c2d233b61 // indirect
	google.golang.org/protobuf v1.35.1 // indirect
	gopkg.in/yaml.v3 v3.0.1 // indirect
)

// TODO: Replace with published version once openshift-eng/openshift-tests-extension is available upstream
// For PoC/testing: clone https://github.com/openshift-eng/openshift-tests-extension to parent directory
replace github.com/openshift-eng/openshift-tests-extension => ../../openshift-tests-extension
