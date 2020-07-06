package custom

import (
	"fmt"
	"io/ioutil"
	"net/http"

	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
)

var (
	conf = &oauth2.Config{
		ClientID:     "511815388398-ng379ngbt3ivpno3all76540eh11ebu7.apps.googleusercontent.com",
		ClientSecret: "0mQogdczWFnNemnVp5esDuas",
		Scopes:       []string{"https://www.googleapis.com/auth/cloud-platform"},
		Endpoint:     google.Endpoint,
		RedirectURL:  "http://example.com",
	}
)

func main() {

	url := conf.AuthCodeURL("state")

	resp, err := http.Get(url)
	if err != nil {
		fmt.Println(err)
	}

	b, _ := ioutil.ReadAll(resp.Body)
	fmt.Println("response Code", resp.StatusCode)
	fmt.Println(string(b))

}
