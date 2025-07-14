// Form data types for Mirroring components
export interface MirroringFormData {
  isEnabled: boolean;
  externalReference: string;
  tags: string;
  syncStartDate: string;
  syncValue: string;
  syncUnit: string;
  robotUsername: string;
  username: string;
  password: string;
  verifyTls: boolean;
  httpProxy: string;
  httpsProxy: string;
  noProxy: string;
  unsignedImages: boolean;
}
