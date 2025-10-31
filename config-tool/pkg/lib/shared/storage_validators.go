package shared

import (
	"context"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/Azure/azure-sdk-for-go/sdk/storage/azblob"
	"github.com/aws/aws-sdk-go/aws"
	awscredentials "github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/credentials/ec2rolecreds"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/sts"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"github.com/ncw/swift"
	log "github.com/sirupsen/logrus"
)

// buildEndpoint normalizes endpoint configuration from both Boto2 and Boto3 formats.
func buildEndpoint(endpointURL string, host string, port int, defaultIsSecure bool) (string, bool, error) {
	var endpoint string
	var isSecure bool

	// Prefer endpoint_url if provided (Boto3 style)
	if endpointURL != "" {
		endpoint = endpointURL

		// Determine security from scheme
		if strings.HasPrefix(endpoint, "https://") {
			isSecure = true
			endpoint = strings.TrimPrefix(endpoint, "https://")
		} else if strings.HasPrefix(endpoint, "http://") {
			isSecure = false
			endpoint = strings.TrimPrefix(endpoint, "http://")
		} else {
			// No scheme in endpoint_url, use default
			isSecure = defaultIsSecure
		}
	} else if host != "" {
		// Boto2 style: use host + port
		endpoint = host
		isSecure = defaultIsSecure

		// Append port if provided and not already in host
		if port != 0 {
			endpoint = endpoint + ":" + strconv.Itoa(port)
		}
	} else {
		return "", false, fmt.Errorf("either endpoint_url or host must be provided")
	}

	return endpoint, isSecure, nil
}

// buildSTSEndpointConfig builds endpoint configuration for STS-based storage types (IRSA and STS).
func buildSTSEndpointConfig(args *DistributedStorageArgs) (string, bool, *aws.Config, error) {
	var s3Endpoint string
	var isSecure bool
	awsConfig := &aws.Config{}

	if args.EndpointURL != "" || args.Host != "" {
		var err error
		s3Endpoint, isSecure, err = buildEndpoint(args.EndpointURL, args.Host, args.Port, true)
		if err != nil {
			return "", false, nil, err
		}

		// Reconstruct the full URL with scheme for STS client
		var stsEndpointURL string
		if isSecure {
			stsEndpointURL = "https://" + s3Endpoint
		} else {
			stsEndpointURL = "http://" + s3Endpoint
		}

		awsConfig.Endpoint = aws.String(stsEndpointURL)
		if !isSecure {
			awsConfig.DisableSSL = aws.Bool(true)
		}
	} else {
		// Default to AWS S3
		s3Endpoint = "s3.amazonaws.com"
		isSecure = true
	}

	return s3Endpoint, isSecure, awsConfig, nil
}

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
		log.Debugf("Using local driver storage.")
		return true, []ValidationError{}
	case "RHOCSStorage", "RadosGWStorage", "IBMCloudStorage":
		log.Debugf("Using IBM Cloud/ODF/RadosGW storage.")
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

		log.Debugf("Storage parameters: ")
		log.Debugf("hostname: %s, bucket name: %s, TLS enabled: %t", endpoint, bucketName, isSecure)

		if ok, err := validateMinioGateway(opts, storageName, endpoint, accessKey, secretKey, bucketName, token, isSecure, fgName); !ok {
			errors = append(errors, err)
		}

	case "S3Storage":
		log.Debugf("Using Amazon S3 Storage.")

		if ok, err := ValidateRequiredString(args.S3Bucket, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".s3_bucket", fgName); !ok {
			errors = append(errors, err)
		}

		accessKey = args.S3AccessKey
		secretKey = args.S3SecretKey
		bucketName = args.S3Bucket

		// Build endpoint from either endpoint_url (boto3) or host+port (boto2)
		if args.EndpointURL != "" || args.Host != "" {
			var err error
			endpoint, isSecure, err = buildEndpoint(args.EndpointURL, args.Host, args.Port, true)
			if err != nil {
				errors = append(errors, ValidationError{
					Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
					FieldGroup: fgName,
					Message:    "Invalid endpoint configuration: " + err.Error(),
				})
				return false, errors
			}
		} else {
			// Default to AWS S3
			endpoint = "s3.amazonaws.com"
			isSecure = true
		}

		if len(errors) > 0 {
			return false, errors
		}

		// If no keys are provided, we attempt to use IAM
		if args.S3AccessKey == "" || args.S3SecretKey == "" {

			sess, err := session.NewSession()
			if err != nil {
				newError := ValidationError{
					Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
					FieldGroup: fgName,
					Message:    "Could not create S3 session.",
				}
				errors = append(errors, newError)
				return false, errors
			}

			// Get credentials and set
			appCreds := ec2rolecreds.NewCredentials(sess)
			value, err := appCreds.Get()
			if err != nil {
				newError := ValidationError{
					Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
					FieldGroup: fgName,
					Message:    "No access key or secret key were provided. Attempted to fetch IAM role and failed.",
				}
				errors = append(errors, newError)
				return false, errors
			}

			accessKey = value.AccessKeyID
			secretKey = value.SecretAccessKey
			token = value.SessionToken

		}

		log.Debugf("S3 Storage parameters: ")
		log.Debugf("hostname: %s, bucket name: %s, TLS enabled: %t", endpoint, bucketName, isSecure)

		if ok, err := validateMinioGateway(opts, storageName, endpoint, accessKey, secretKey, bucketName, token, isSecure, fgName); !ok {
			errors = append(errors, err)
		}

	case "IRSAS3Storage":
		log.Debugf("Using IRSA S3 Storage.")

		if ok, err := ValidateRequiredString(args.S3Bucket, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".s3_bucket", fgName); !ok {
			errors = append(errors, err)
		}

		bucketName = args.S3Bucket

		// Build endpoint configuration for STS and S3
		var awsConfig *aws.Config
		var err error
		endpoint, isSecure, awsConfig, err = buildSTSEndpointConfig(args)
		if err != nil {
			errors = append(errors, ValidationError{
				Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
				FieldGroup: fgName,
				Message:    "Invalid endpoint configuration: " + err.Error(),
			})
			return false, errors
		}

		// IRSA uses automatic credential discovery via AWS_WEB_IDENTITY_TOKEN_FILE and AWS_ROLE_ARN
		sess, err := session.NewSession(awsConfig)
		if err != nil {
			newError := ValidationError{
				Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
				FieldGroup: fgName,
				Message:    "Could not create S3 session for IRSA. Error: " + err.Error(),
			}
			errors = append(errors, newError)
			return false, errors
		}

		// Get temp credentials from the default credential chain (includes web identity token)
		creds, err := sess.Config.Credentials.Get()
		if err != nil {
			newError := ValidationError{
				Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
				FieldGroup: fgName,
				Message:    "Could not fetch IRSA credentials. Ensure AWS_WEB_IDENTITY_TOKEN_FILE and AWS_ROLE_ARN are set. Error: " + err.Error(),
			}
			errors = append(errors, newError)
			return false, errors
		}

		accessKey = creds.AccessKeyID
		secretKey = creds.SecretAccessKey
		token = creds.SessionToken

		log.Debugf("IRSA S3 Storage parameters: ")
		log.Debugf("hostname: %s, bucket name: %s, TLS enabled: %t", endpoint, bucketName, isSecure)

		if ok, err := validateMinioGateway(opts, storageName, endpoint, accessKey, secretKey, bucketName, token, isSecure, fgName); !ok {
			errors = append(errors, err)
		}

	case "STSS3Storage":
		log.Debugf("Using STS S3 Storage.")
		// Check bucket name
		if ok, err := ValidateRequiredString(args.S3Bucket, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".s3_bucket", fgName); !ok {
			errors = append(errors, err)
		}

		roleArn := args.STSRoleArn
		if roleArn == "" {
			roleArn = os.Getenv("AWS_ROLE_ARN")
		}
		roleToAssumeArn := roleArn
		durationSeconds := int64(3600)

		webIdentityTokenFile := args.STSWebIdentityTokenFile
		// Only check the Web Identity Token File variable if no other credentials are present in the config
		if args.STSUserAccessKey == "" && args.STSUserSecretKey == "" && args.STSWebIdentityTokenFile == "" {
			webIdentityTokenFile = os.Getenv("AWS_WEB_IDENTITY_TOKEN_FILE")
		}

		// Get the session name, defaulting to "quay" if not provided
		sessionName := args.STSRoleSessionName
		if sessionName == "" {
			sessionName = os.Getenv("AWS_ROLE_SESSION_NAME")
		}
		if sessionName == "" {
			sessionName = "quay"
		}

		// Build endpoint configuration for STS and S3
		var awsConfig *aws.Config
		endpoint, isSecure, awsConfig, err := buildSTSEndpointConfig(args)
		if err != nil {
			errors = append(errors, ValidationError{
				Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
				FieldGroup: fgName,
				Message:    "Invalid endpoint configuration: " + err.Error(),
			})
			return false, errors
		}

		var credentials *sts.Credentials
		// Prefer using web tokens to authenticate and fallback to access and secret keys
		if webIdentityTokenFile != "" {
			sess := session.Must(session.NewSession(awsConfig))
			svc := sts.New(sess)
			webIdentityToken, err := os.ReadFile(webIdentityTokenFile)
			if err != nil {
				errors = append(errors, ValidationError{
					Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
					FieldGroup: fgName,
					Message:    "Could not read the STS Web Identity Token File, Error: " + err.Error(),
				})
				break
			}
			assumeRoleInput := &sts.AssumeRoleWithWebIdentityInput{
				RoleArn:          aws.String(roleToAssumeArn),
				RoleSessionName:  aws.String(sessionName),
				DurationSeconds:  aws.Int64(durationSeconds),
				WebIdentityToken: aws.String(string(webIdentityToken)),
			}
			assumeRoleOutput, err := svc.AssumeRoleWithWebIdentity(assumeRoleInput)
			if err != nil {
				errors = append(errors, ValidationError{
					Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
					FieldGroup: fgName,
					Message:    "Could not fetch credentials from STS with Web Identity Token. Error: " + err.Error(),
				})
				break
			}
			credentials = assumeRoleOutput.Credentials
		} else {
			awsConfig.Credentials = awscredentials.NewStaticCredentials(args.STSUserAccessKey, args.STSUserSecretKey, "")
			sess := session.Must(session.NewSession(awsConfig))
			svc := sts.New(sess)
			assumeRoleInput := &sts.AssumeRoleInput{
				RoleArn:         aws.String(roleToAssumeArn),
				RoleSessionName: aws.String(sessionName),
				DurationSeconds: aws.Int64(durationSeconds),
			}
			assumeRoleOutput, err := svc.AssumeRole(assumeRoleInput)
			if err != nil {
				errors = append(errors, ValidationError{
					Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
					FieldGroup: fgName,
					Message:    "Could not fetch credentials from STS. Error: " + err.Error(),
				})
				break
			}
			credentials = assumeRoleOutput.Credentials
		}

		accessKey := *credentials.AccessKeyId
		secretKey := *credentials.SecretAccessKey
		token = *credentials.SessionToken
		bucketName = args.S3Bucket

		log.Debugf("STS S3 Storage parameters: ")
		log.Debugf("hostname: %s, bucket name: %s, TLS enabled: %t", endpoint, bucketName, isSecure)

		if ok, err := validateMinioGateway(opts, storageName, endpoint, accessKey, secretKey, bucketName, token, isSecure, fgName); !ok {
			errors = append(errors, err)
		}

	case "GoogleCloudStorage":
		log.Debugf("Using Google Cloud Storage.")
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

		accessKey = args.AccessKey
		secretKey = args.SecretKey
		endpoint = "storage.googleapis.com"
		isSecure = true
		bucketName = args.BucketName

		if len(errors) > 0 {
			return false, errors
		}

		log.Debugf("GCS Storage parameters: ")
		log.Debugf("hostname: %s, bucket name: %s, TLS enabled: %t", endpoint, bucketName, isSecure)

		if ok, err := validateMinioGateway(opts, storageName, endpoint, accessKey, secretKey, bucketName, token, isSecure, fgName); !ok {
			errors = append(errors, err)
		}

	case "AzureStorage":
		log.Debugf("Using Azure storage.")

		// Check access key
		if ok, err := ValidateRequiredString(args.AzureContainer, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".azure_container", fgName); !ok {
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
		if args.EndpointURL != "" {
			endpoint = args.EndpointURL
		} else {
			endpoint = fmt.Sprintf("https://%s.blob.core.windows.net", accountName)
		}

		if len(errors) > 0 {
			return false, errors
		}

		log.Debugf("Azure Storage parameters: ")
		log.Debugf("hostname: %s, account name: %s, container name: %s.", endpoint, accountName, containerName)

		if ok, err := validateAzureGateway(opts, endpoint, storageName, accountName, accountKey, containerName, token, fgName); !ok {
			errors = append(errors, err)
		}

	case "CloudFrontedS3Storage":
		log.Debugf("Using CloudFront S3 storage.")
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

		// Build endpoint from either endpoint_url (boto3) or host+port (boto2)
		if args.EndpointURL != "" || args.Host != "" {
			var err error
			endpoint, isSecure, err = buildEndpoint(args.EndpointURL, args.Host, args.Port, true)
			if err != nil {
				errors = append(errors, ValidationError{
					Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
					FieldGroup: fgName,
					Message:    "Invalid endpoint configuration: " + err.Error(),
				})
				return false, errors
			}
		} else {
			// Default to AWS S3
			endpoint = "s3.amazonaws.com"
			isSecure = true
		}

		if len(errors) > 0 {
			return false, errors
		}

		log.Debugf("CloudFront S3 Storage parameters: ")
		log.Debugf("hostname: %s, bucket name: %s, TLS enabled: %t", endpoint, bucketName, isSecure)

		// Validate bucket settings
		if ok, err := validateMinioGateway(opts, storageName, endpoint, accessKey, secretKey, bucketName, token, isSecure, fgName); !ok {
			errors = append(errors, err)
		}

		_, err := session.NewSession(&aws.Config{
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

	case "SwiftStorage":
		log.Debugf("Swift Storage setup.")

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

		log.Debugf("Swift Storage parameters: ")
		log.Debugf("hostname: %s, container: %s, auth version: %d", args.SwiftAuthURL, args.SwiftContainer, args.SwiftAuthVersion)

		if ok, err := validateSwift(opts, storageName, args.SwiftAuthVersion, args.SwiftUser, args.SwiftPassword, args.SwiftContainer, args.SwiftAuthURL, args.SwiftOsOptions, fgName); !ok {
			errors = append(errors, err)
		}
	case "CloudFlareStorage":
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
		// Check distribution domain
		if ok, err := ValidateRequiredString(args.CloudflareDomain, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".cloudflare_domain", fgName); !ok {
			errors = append(errors, err)
		}
	case "MultiCDNStorage":
		// Check provider map
		if ok, err := ValidateRequiredObject(args.Providers, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".providers", fgName); !ok {
			errors = append(errors, err)
		}

		// Check default provider
		if ok, err := ValidateRequiredString(args.DefaultProvider, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".default_provider", fgName); !ok {
			errors = append(errors, err)
		}

		// Check storage config
		if ok, err := ValidateRequiredObject(args.StorageConfig, "DISTRIBUTED_STORAGE_CONFIG."+storageName+".storage_config", fgName); !ok {
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

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
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

func validateAzureGateway(opts Options, endpointURL, storageName, accountName, accountKey, containerName, token, fgName string) (bool, ValidationError) {

	credential, err := azblob.NewSharedKeyCredential(accountName, accountKey)
	if err != nil {
		return false, ValidationError{
			FieldGroup: fgName,
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			Message:    "Could not create credentials for Azure storage. Error: " + err.Error(),
		}
	}

	client, err := azblob.NewClientWithSharedKeyCredential(endpointURL, credential, nil)
	if err != nil {
		return false, ValidationError{
			FieldGroup: fgName,
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			Message:    "Could not create Azure storage client. Error: " + err.Error(),
		}
	}

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	// Verify the container exists
	containerClient := client.ServiceClient().NewContainerClient(containerName)
	_, err = containerClient.GetProperties(ctx, nil)
	if err != nil {
		return false, ValidationError{
			FieldGroup: fgName,
			Tags:       []string{"DISTRIBUTED_STORAGE_CONFIG"},
			Message:    "Could not access container in Azure storage. Error: " + err.Error(),
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
