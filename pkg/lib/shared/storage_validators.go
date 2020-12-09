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
	"github.com/aws/aws-sdk-go/aws"
	awscredentials "github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/cloudfront"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"github.com/ncw/swift"
)

// ValidateStorage will validate a S3 storage connection.
func ValidateStorage(opts Options, storageName string, storageType string, args *DistributedStorageArgs, fgName string) (bool, []ValidationError) {

	errors := []ValidationError{}

	// Get credentials
	var endpoint string
	var accessKey string
	var secretKey string
	var isSecure bool
	var bucketName string
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
		bucketName = args.BucketName

		// Append port if present
		if args.Port != 0 {
			endpoint = endpoint + ":" + strconv.Itoa(args.Port)
		}

		if len(errors) > 0 {
			return false, errors
		}

		if ok, err := validateMinioGateway(opts, storageName, endpoint, accessKey, secretKey, bucketName, token, isSecure, fgName); !ok {
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
		bucketName = args.S3Bucket
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

		if ok, err := validateMinioGateway(opts, storageName, endpoint, accessKey, secretKey, bucketName, token, isSecure, fgName); !ok {
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
		bucketName = args.BucketName

		if len(errors) > 0 {
			return false, errors
		}

		if ok, err := validateMinioGateway(opts, storageName, endpoint, accessKey, secretKey, bucketName, token, isSecure, fgName); !ok {
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

	case "CloudFrontedS3Storage":

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
		// Check distribution domain
		if ok, err := ValidateRequiredString(args.CloudfrontDistributionDomain, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".cloudfront_distribution_domain", fgName); !ok {
			errors = append(errors, err)
		}
		// Check key id
		if ok, err := ValidateRequiredString(args.CloudfrontKeyID, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".cloudfront_key_id", fgName); !ok {
			errors = append(errors, err)
		}

		accessKey = args.S3AccessKey
		secretKey = args.S3SecretKey
		bucketName = args.S3Bucket
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

		// Validate bucket settings
		if ok, err := validateMinioGateway(opts, storageName, endpoint, accessKey, secretKey, bucketName, token, isSecure, fgName); !ok {
			errors = append(errors, err)
		}

		sess, err := session.NewSession(&aws.Config{
			Credentials: awscredentials.NewStaticCredentials(accessKey, secretKey, ""),
		})
		if err != nil {
			newError := ValidationError{
				Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
				FieldGroup: fgName,
				Message:    "Could not create S3 session",
			}
			errors = append(errors, newError)
			return false, errors
		}

		// Validate distribution
		svc := cloudfront.New(sess)
		res, err := svc.ListDistributions(&cloudfront.ListDistributionsInput{})
		if err != nil {
			newError := ValidationError{
				Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
				FieldGroup: fgName,
				Message:    "Could not list CloudFront distributions. Error: " + err.Error(),
			}
			errors = append(errors, newError)
			return false, errors
		}

		found := false
		for _, distribution := range res.DistributionList.Items {
			if *distribution.DomainName == args.CloudfrontDistributionDomain {
				found = true
				break
			}
		}

		if !found {
			err = fmt.Errorf("No CloudFront distribution exists with given domain name (%s)", args.CloudfrontDistributionDomain)
			newError := ValidationError{
				Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
				FieldGroup: fgName,
				Message:    "Could not get CloudFront distribution. Error: " + err.Error(),
			}
			errors = append(errors, newError)
			return false, errors
		}

		_, err = svc.GetPublicKey(&cloudfront.GetPublicKeyInput{Id: &args.CloudfrontKeyID})
		if err != nil {
			newError := ValidationError{
				Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
				FieldGroup: fgName,
				Message:    "Could not get CloudFront public key. Error: " + err.Error(),
			}
			errors = append(errors, newError)
			return false, errors
		}

	case "SwiftStorage":

		// Validate auth version
		if args.SwiftAuthVersion != 1 && args.SwiftAuthVersion != 2 && args.SwiftAuthVersion != 3 {
			newError := ValidationError{
				Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
				FieldGroup: fgName,
				Message:    strconv.Itoa(args.SwiftAuthVersion) + " must be either 1, 2, or 3.",
			}
			errors = append(errors, newError)
		}
		// Check auth url
		if ok, err := ValidateRequiredString(args.SwiftAuthURL, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".auth_url", fgName); !ok {
			errors = append(errors, err)
		}
		// Check swift container
		if ok, err := ValidateRequiredString(args.SwiftContainer, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".swift_container", fgName); !ok {
			errors = append(errors, err)
		}
		// Check storage path
		if ok, err := ValidateRequiredString(args.StoragePath, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".storage_path", fgName); !ok {
			errors = append(errors, err)
		}
		// Check swift user
		if ok, err := ValidateRequiredString(args.SwiftUser, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".swift_user", fgName); !ok {
			errors = append(errors, err)
		}
		// Check swift password
		if ok, err := ValidateRequiredString(args.SwiftPassword, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".swift_password", fgName); !ok {
			errors = append(errors, err)
		}

		if len(errors) > 0 {
			return false, errors
		}

		if ok, err := validateSwift(opts, storageName, args.SwiftAuthVersion, args.SwiftUser, args.SwiftPassword, args.SwiftContainer, args.SwiftAuthURL, args.SwiftOsOptions, fgName); !ok {
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

func validateMinioGateway(opts Options, storageName, endpoint, accessKey, secretKey, bucketName, token string, isSecure bool, fgName string) (bool, ValidationError) {

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

	found, err := st.BucketExists(ctx, bucketName)
	if err != nil {
		newError := ValidationError{
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			FieldGroup: fgName,
			Message:    "Could not connect to storage " + storageName + ". Error: " + err.Error(),
		}
		return false, newError
	}

	if !found {
		newError := ValidationError{
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			FieldGroup: fgName,
			Message:    fmt.Sprintf("Could not find bucket (%s) in storage (%s)", bucketName, storageName),
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

func validateSwift(opts Options, storageName string, authVersion int, swiftUser, swiftPassword, containerName, authUrl string, osOptions map[string]interface{}, fgName string) (bool, ValidationError) {

	var c swift.Connection
	switch authVersion {
	case 1:
		c = swift.Connection{
			UserName:    swiftUser,
			ApiKey:      swiftPassword,
			AuthUrl:     authUrl,
			AuthVersion: 1,
		}
	case 2:
		c = swift.Connection{
			UserName:    swiftUser,
			ApiKey:      swiftPassword,
			AuthUrl:     authUrl,
			AuthVersion: 2,
		}
	case 3:

		// Need domain
		domain, ok := osOptions["user_domain_name"].(string)
		if !ok {
			return false, ValidationError{
				FieldGroup: fgName,
				Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
				Message:    "Swift auth v3 requires a domain (string) in os_options",
			}
		}
		// Need domain
		tenantId, ok := osOptions["tenant_id"].(string)
		if !ok {
			return false, ValidationError{
				FieldGroup: fgName,
				Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
				Message:    "Swift auth v3 requires tenant_id (string) in os_options",
			}
		}
		c = swift.Connection{
			UserName:    swiftUser,
			ApiKey:      swiftPassword,
			AuthUrl:     authUrl,
			AuthVersion: 3,
			Domain:      domain,
			TenantId:    tenantId,
		}
	}

	err := c.Authenticate()
	if err != nil {
		return false, ValidationError{
			FieldGroup: fgName,
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			Message:    "Could not connect to Swift storage. Error: " + err.Error(),
		}
	}

	// List containers
	containers, err := c.ContainerNames(nil)
	if err != nil {
		return false, ValidationError{
			FieldGroup: fgName,
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			Message:    "Could not list containers in Swift storage. Error: " + err.Error(),
		}
	}

	// Validate container name is present
	for _, name := range containers {
		if containerName == name {
			return true, ValidationError{}
		}
	}

	return false, ValidationError{
		FieldGroup: fgName,
		Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
		Message:    fmt.Sprintf("Could not find container (%s) in Swift storage.", containerName),
	}

}
