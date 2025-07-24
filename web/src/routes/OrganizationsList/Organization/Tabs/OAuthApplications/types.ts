export interface OAuthApplicationFormData {
  name: string;
  application_uri: string;
  description: string;
  avatar_email: string;
  redirect_uri: string;
}

export const defaultOAuthFormValues: OAuthApplicationFormData = {
  name: '',
  application_uri: '',
  description: '',
  avatar_email: '',
  redirect_uri: '',
};
