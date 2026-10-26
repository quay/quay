package auth

import (
	"regexp"
	"strings"
	"unicode/utf8"
)

var usernamePattern = regexp.MustCompile(`^[a-z0-9]+(?:[._-][a-z0-9]+)*$`)

func parseRobotUsername(username string) (owner, shortname string, ok bool) {
	if strings.Count(username, "+") != 1 {
		return "", "", false
	}

	owner, shortname, ok = strings.Cut(username, "+")
	if !ok || !validUsername(owner) || !validUsername(shortname) {
		return "", "", false
	}

	return owner, shortname, true
}

func isRobotUsername(username string) bool {
	_, _, ok := parseRobotUsername(username)
	return ok
}

func validUsername(username string) bool {
	if len(username) < 2 || len(username) > 255 {
		return false
	}
	return usernamePattern.MatchString(username)
}

func isASCII(s string) bool {
	for s != "" {
		r, size := utf8.DecodeRuneInString(s)
		if r == utf8.RuneError && size == 1 {
			return false
		}
		if r > 0x7f {
			return false
		}
		s = s[size:]
	}
	return true
}
