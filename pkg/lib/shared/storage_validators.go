package shared

import (
	"context"
	"fmt"
	"log"
	"net/url"
	"regexp"
	"strconv"
	"time"

	"github.com/Azure/azure-storage-blob-go/azblob"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

// ValidateStorage will validate a S3 storage connection.
func ValidateStorage(opts Options, storageName string, storageType string, args *DistributedStorageArgs, fgName string) (bool, []ValidationError) {

	errors := []ValidationError{}

	// Get credentials
	var endpoint string
	var accessKey string
	var secretKey string
	var isSecure bool
	var token string = ""

	switch storageType {
	case "LocalStorage":
		return true, []ValidationError{}
	case "RHOCSStorage", "RadosGWStorage":

		// Check access key
		if ok, err := ValidateRequiredString(args.AccessKey, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".access_key", fgName); !ok {
			errors = append(errors, err)
		}
		// Check secret key
		if ok, err := ValidateRequiredString(args.SecretKey, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".secret_key", fgName); !ok {
			errors = append(errors, err)
		}
		// Check hostname
		if ok, err := ValidateRequiredString(args.Hostname, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".hostname", fgName); !ok {
			errors = append(errors, err)
		}
		// Check bucket name
		if ok, err := ValidateRequiredString(args.BucketName, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".bucket_name", fgName); !ok {
			errors = append(errors, err)
		}
		// Check bucket name
		if ok, err := ValidateRequiredString(args.StoragePath, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".storage_path", fgName); !ok {
			errors = append(errors, err)
		}

		// Grab necessary variables
		accessKey = args.AccessKey
		secretKey = args.SecretKey
		endpoint = args.Hostname
		isSecure = args.IsSecure

		// Append port if present
		if args.Port != 0 {
			endpoint = endpoint + ":" + strconv.Itoa(args.Port)
		}

		if len(errors) > 0 {
			return false, errors
		}

		if ok, err := validateMinioGateway(opts, storageName, endpoint, accessKey, secretKey, token, isSecure, fgName); !ok {
			errors = append(errors, err)
		}

	case "S3Storage":

		// Check access key
		if ok, err := ValidateRequiredString(args.S3AccessKey, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".s3_access_key", fgName); !ok {
			errors = append(errors, err)
		}
		// Check secret key
		if ok, err := ValidateRequiredString(args.S3SecretKey, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".s3_secret_key", fgName); !ok {
			errors = append(errors, err)
		}
		// Check bucket name
		if ok, err := ValidateRequiredString(args.S3Bucket, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".s3_bucket", fgName); !ok {
			errors = append(errors, err)
		}
		// Check storage path
		if ok, err := ValidateRequiredString(args.StoragePath, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".storage_path", fgName); !ok {
			errors = append(errors, err)
		}

		accessKey = args.S3AccessKey
		secretKey = args.S3SecretKey
		isSecure = true

		if len(args.Host) == 0 {
			endpoint = "s3.amazonaws.com"
		} else {
			endpoint = args.Host
		}
		if args.Port != 0 {
			endpoint = endpoint + ":" + strconv.Itoa(args.Port)
		}

		if len(errors) > 0 {
			return false, errors
		}

		if ok, err := validateMinioGateway(opts, storageName, endpoint, accessKey, secretKey, token, isSecure, fgName); !ok {
			errors = append(errors, err)
		}

	case "GoogleCloudStorage":

		// Check access key
		if ok, err := ValidateRequiredString(args.AccessKey, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".access_key", fgName); !ok {
			errors = append(errors, err)
		}
		// Check secret key
		if ok, err := ValidateRequiredString(args.SecretKey, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".secret_key", fgName); !ok {
			errors = append(errors, err)
		}
		// Check bucket name
		if ok, err := ValidateRequiredString(args.BucketName, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".bucket_name", fgName); !ok {
			errors = append(errors, err)
		}
		// Check storage path
		if ok, err := ValidateRequiredString(args.StoragePath, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".storage_path", fgName); !ok {
			errors = append(errors, err)
		}

		accessKey = args.AccessKey
		secretKey = args.SecretKey
		endpoint = "storage.googleapis.com"

		if len(errors) > 0 {
			return false, errors
		}

		if ok, err := validateMinioGateway(opts, storageName, endpoint, accessKey, secretKey, token, isSecure, fgName); !ok {
			errors = append(errors, err)
		}

	case "AzureStorage":

		// Check access key
		if ok, err := ValidateRequiredString(args.AzureContainer, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".azure_container", fgName); !ok {
			errors = append(errors, err)
		}
		// Check storage path
		if ok, err := ValidateRequiredString(args.StoragePath, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".storage_path", fgName); !ok {
			errors = append(errors, err)
		}
		// Check account name
		if ok, err := ValidateRequiredString(args.AzureAccountName, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".azure_account_name", fgName); !ok {
			errors = append(errors, err)
		}

		accountName := args.AzureAccountName
		accountKey := args.AzureAccountKey
		containerName := args.AzureContainer
		token = args.SASToken

		if len(errors) > 0 {
			return false, errors
		}

		if ok, err := validateAzureGateway(opts, storageName, accountName, accountKey, containerName, token, fgName); !ok {
			errors = append(errors, err)
		}

	default:
		newError := ValidationError{
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			FieldGroup: fgName,
			Message:    storageType + " is not a valid storage type.",
		}
		return false, []ValidationError{newError}
	}

	if len(errors) > 0 {
		return false, errors
	} else {
		return true, nil
	}

}

func validateMinioGateway(opts Options, storageName, endpoint, accessKey, secretKey, token string, isSecure bool, fgName string) (bool, ValidationError) {

	// Set transport
	tr, err := minio.DefaultTransport(true)
	if err != nil {
		log.Fatalf("error creating the minio connection: error creating the default transport layer: %v", err)
	}

	config, err := GetTlsConfig(opts)
	if err != nil {
		newError := ValidationError{
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			FieldGroup: fgName,
			Message:    err.Error(),
		}
		return false, newError
	}
	tr.TLSClientConfig = config

	// Create client
	st, err := minio.New(endpoint, &minio.Options{
		Creds:     credentials.NewStaticV4(accessKey, secretKey, token),
		Secure:    isSecure,
		Transport: tr,
	})
	if err != nil {
		newError := ValidationError{
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			FieldGroup: fgName,
			Message:    "An error occurred while attempting to connect to " + storageName + " storage. Error: " + err.Error(),
		}
		return false, newError
	}

	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
	defer cancel()

	_, err = st.ListBuckets(ctx)
	if err != nil {
		newError := ValidationError{
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			FieldGroup: fgName,
			Message:    "Could not connect to storage " + storageName + ". Error: " + err.Error(),
		}
		return false, newError
	}

	return true, ValidationError{}

}

func validateAzureGateway(opts Options, storageName, accountName, accountKey, containerName, token, fgName string) (bool, ValidationError) {

	credentials, err := azblob.NewSharedKeyCredential(accountName, accountKey)
	if err != nil {
		return false, ValidationError{
			FieldGroup: fgName,
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			Message:    "Could not create credentials for Azure storage. Error: " + err.Error(),
		}
	}

	p := azblob.NewPipeline(credentials, azblob.PipelineOptions{})
	u, err := url.Parse(fmt.Sprintf("https://%s.blob.core.windows.net", accountName))

	serviceURL := azblob.NewServiceURL(*u, p)
	containerURL := serviceURL.NewContainerURL(containerName)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	_, err = containerURL.GetAccountInfo(ctx)
	if err != nil {
		re := regexp.MustCompile(`Code: (\w+)`)
		message := re.FindStringSubmatch(err.Error())
		return false, ValidationError{
			FieldGroup: fgName,
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			Message:    "Could not connect to Azure storage. Error: " + message[1],
		}
	}

	return true, ValidationError{}

}
