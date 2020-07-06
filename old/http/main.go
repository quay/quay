package main

import (
	"fmt"

	"github.com/markbates/goth/providers/github"
)

func main() {

	p := github.New("fc0ef3cf19f90de48af9", "8bd923a5768a59f2e5f848752fa71ae62f4991ce", "")

	sess, err := p.BeginAuth("")
	if err != nil {
		fmt.Println(err.Error())
	}

}
