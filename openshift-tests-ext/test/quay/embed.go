package quay

import (
	"embed"
)

//go:embed scenarios.json
var QuayScenarios []byte

//go:embed scripts/*
var QuayScripts embed.FS
