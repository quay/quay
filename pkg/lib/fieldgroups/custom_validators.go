package fieldgroups

import (
	"regexp"

	"github.com/go-playground/validator/v10"
)

func customValidateTimePattern(fl validator.FieldLevel) bool {

	re := regexp.MustCompile(`^[0-9]+(w|m|d|h|s)$`)
	matches := re.FindAllString(fl.Field().String(), -1)

	if len(matches) != 1 {
		return false
	}

	return true

}
