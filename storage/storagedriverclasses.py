from storage.local import LocalStorage
from storage.cloud import (
    S3Storage,
    GoogleCloudStorage,
    RadosGWStorage,
    RHOCSStorage,
    CloudFrontedS3Storage,
)
from storage.swift import SwiftStorage
from storage.azurestorage import AzureStorage
from storage.cloudflarestorage import CloudFlareS3Storage

STORAGE_DRIVER_CLASSES = {
    "LocalStorage": LocalStorage,
    "S3Storage": S3Storage,
    "GoogleCloudStorage": GoogleCloudStorage,
    "RadosGWStorage": RadosGWStorage,
    "SwiftStorage": SwiftStorage,
    "CloudFrontedS3Storage": CloudFrontedS3Storage,
    "AzureStorage": AzureStorage,
    "RHOCSStorage": RHOCSStorage,
    "CloudFlareStorage": CloudFlareS3Storage,
}
