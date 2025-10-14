import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {useCurrentUser} from './UseCurrentUser';
import {useQuayConfig} from './UseQuayConfig';
import axios from 'src/libs/axios';
import {assertHttpCode} from 'src/resources/ErrorHandling';

interface AuthorizedApp {
  uuid: string;
  application: {
    name: string;
    description?: string;
    url?: string;
    avatar: {
      name: string;
      hash: string;
      command: string[];
      kind: string;
    };
    organization: {
      name: string;
    };
    clientId: string;
  };
  scopes: Array<{
    scope: string;
    description: string;
  }>;
  responseType?: string;
  redirectUri?: string;
}

async function fetchAuthorizedApplications(): Promise<AuthorizedApp[]> {
  const response = await axios.get('/api/v1/user/authorizations');
  assertHttpCode(response.status, 200);
  return response.data.authorizations || [];
}

async function fetchAssignedAuthorizations(): Promise<AuthorizedApp[]> {
  const response = await axios.get('/api/v1/user/assignedauthorization');
  assertHttpCode(response.status, 200);
  return response.data.authorizations || [];
}

async function revokeAuthorization(uuid: string): Promise<void> {
  const response = await axios.delete(`/api/v1/user/authorizations/${uuid}`);
  assertHttpCode(response.status, 204);
}

async function deleteAssignedAuthorization(uuid: string): Promise<void> {
  const response = await axios.delete(
    `/api/v1/user/assignedauthorization/${uuid}`,
  );
  assertHttpCode(response.status, 204);
}

export function useAuthorizedApplications() {
  const {user} = useCurrentUser();
  const config = useQuayConfig();
  const queryClient = useQueryClient();

  const {
    data: authorizedApps = [],
    isLoading: loadingAuthorized,
    error: authorizedError,
  } = useQuery(['authorizedApplications'], fetchAuthorizedApplications, {
    enabled: !!user,
  });

  const {
    data: assignedApps = [],
    isLoading: loadingAssigned,
    error: assignedError,
  } = useQuery(['assignedAuthorizations'], fetchAssignedAuthorizations, {
    enabled: !!user && !!config?.features?.ASSIGN_OAUTH_TOKEN,
  });

  const revokeMutation = useMutation(revokeAuthorization, {
    onSuccess: () => {
      queryClient.invalidateQueries(['authorizedApplications']);
    },
  });

  const deleteAssignedMutation = useMutation(deleteAssignedAuthorization, {
    onSuccess: () => {
      queryClient.invalidateQueries(['assignedAuthorizations']);
    },
  });

  const getAuthorizationUrl = (app: AuthorizedApp) => {
    const scopes = app.scopes.map((scope) => scope.scope).join(' ');
    const params = new URLSearchParams({
      response_type: app.responseType || 'code',
      client_id: app.application.clientId,
      scope: scopes,
      redirect_uri: app.redirectUri || '',
      assignment_uuid: app.uuid,
    });
    return `${window.location.origin}/oauth/authorize?${params.toString()}`;
  };

  return {
    authorizedApps,
    assignedApps,
    isLoading: loadingAuthorized || loadingAssigned,
    error: authorizedError || assignedError,
    revokeAuthorization: revokeMutation.mutate,
    deleteAssignedAuthorization: deleteAssignedMutation.mutate,
    getAuthorizationUrl,
    isRevoking: revokeMutation.isLoading,
    isDeletingAssigned: deleteAssignedMutation.isLoading,
  };
}
