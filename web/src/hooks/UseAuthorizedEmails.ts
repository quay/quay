import {
  AuthorizedEmail,
  fetchAuthorizedEmail,
  sendAuthorizedEmail,
} from 'src/resources/AuthorizedEmailResource';
import {AxiosError} from 'axios';
import {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';

export interface AuthorizedEmailStatus {
  emailData: AuthorizedEmail;
  exists: boolean;
  error: Error;
}

export function useAuthorizedEmails(org: string, repo: string) {
  const [pollEmail, setPollEmail] = useState<string>('');
  const [emailConfirmed, setEmailConfirmed] = useState<boolean>(false);
  const polling = pollEmail != '';
  const startPolling = (email: string) => setPollEmail(email);
  const stopPolling = () => setPollEmail('');
  const resetEmailConfirmed = () => setEmailConfirmed(false);

  const {isError: errorPolling} = useQuery(
    ['pollauthorizedemail', org, repo, pollEmail],
    () => fetchAuthorizedEmail(org, repo, pollEmail),
    {
      enabled: polling,
      refetchInterval: (emailData: AuthorizedEmail) => {
        if (emailData != null && emailData.confirmed) {
          setEmailConfirmed(true);
          stopPolling();
          return false;
        } else {
          return 5000;
        }
      },
      onError: () => stopPolling(),
    },
  );

  const {
    mutate: sendEmail,
    isError: errorSendingEmail,
    isSuccess: successSendingEmail,
    reset,
  } = useMutation(async (email: string) =>
    sendAuthorizedEmail(org, repo, email),
  );

  return {
    polling: polling,
    errorPolling: errorPolling,
    startPolling: startPolling,
    stopPolling: stopPolling,
    emailConfirmed: emailConfirmed,
    resetEmailConfirmed: resetEmailConfirmed,

    sendAuthorizedEmail: sendEmail,
    successSendingAuthorizedEmail: successSendingEmail,
    errorSendingAuthorizedEmail: errorSendingEmail,
    resetSendAuthorizationEmail: reset,
  };
}
