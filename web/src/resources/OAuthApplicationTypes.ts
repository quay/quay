export interface IOAuthApplication {
  application_uri: string;
  avatar_email: string;
  client_id: string;
  client_secret: string;
  description: string;
  name: string;
  redirect_uri: string;
}

export interface CreateOAuthApplicationParams {
  name: string;
  redirect_uri: string;
  application_uri: string;
  description: string;
  avatar_email: string;
}

export interface IOAuthApplicationToken {
  uuid: string;
  name: string | null;
  scope: string;
  expires_at: string | null;
  created: string | null;
  created_by: string | null;
  last_accessed: string | null;
  token?: string;
}

export interface OAuthApplicationTokensResponse {
  tokens: IOAuthApplicationToken[];
  next_page?: string;
}

export interface CreateOAuthApplicationTokenParams {
  name: string;
  scope: string;
  expiration: number;
}

export interface AssignOAuthApplicationTokenParams {
  username: string;
  scope: string;
  redirect_uri: string;
}
