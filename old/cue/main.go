package main

import (
	"fmt"
	"io/ioutil"

	"cuelang.org/go/cue"
	"cuelang.org/go/encoding/gocode"
)

func main() {

	// read file
	b, err := ioutil.ReadFile("schema.cue")
	if err != nil {
		fmt.Println(err.Error())
	}

	var r cue.Runtime

	instance, _ := r.Compile("test", b)

	bytes, err := gocode.Generate("", instance, nil)
	if err != nil {
		// handle error
	}

	err = ioutil.WriteFile("cue_gen.go", bytes, 0644)

}
