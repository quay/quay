import {useEffect, useRef, useState, useCallback} from 'react';
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {isAxiosError} from 'axios';
import {
  OrgMirrorConfig,
  CreateOrgMirrorConfig,
  getOrgMirrorConfig,
  createOrgMirrorConfig,
  updateOrgMirrorConfig,
  syncOrgMirrorNow,
  cancelOrgMirrorSync,
  verifyOrgMirrorConnection,
} from 'src/resources/OrgMirrorResource';
import {OrgMirroringFormData} from 'src/routes/OrganizationsList/Organization/Tabs/OrgMirroring/types';
import {
  convertToSeconds,
  convertFromSeconds,
  formatDateForInput,
} from 'src/libs/utils';
import {SourceRegistryType} from 'src/resources/OrgMirrorResource';
import {
  SyncUnit,
  Visibility,
} from 'src/routes/OrganizationsList/Organization/Tabs/OrgMirroring/types';
import {Entity, EntityKind} from 'src/resources/UserResource';

const ORG_MIRROR_QUERY_KEY = 'org-mirror-config';

// Valid values for runtime validation of API responses
const VALID_REGISTRY_TYPES: SourceRegistryType[] = ['harbor', 'quay'];
const VALID_VISIBILITIES: Visibility[] = ['public', 'private'];
const VALID_SYNC_UNITS: SyncUnit[] = [
  'seconds',
  'minutes',
  'hours',
  'days',
  'weeks',
];

// Convert API config to form data for populating the form
export const configToFormData = (
  response: OrgMirrorConfig,
): OrgMirroringFormData => {
  const {value, unit} = convertFromSeconds(response.sync_interval);
  return {
    isEnabled: response.is_enabled,
    externalRegistryType: VALID_REGISTRY_TYPES.includes(
      response.external_registry_type as SourceRegistryType,
    )
      ? (response.external_registry_type as SourceRegistryType)
      : 'harbor',
    externalRegistryUrl: response.external_registry_url || '',
    externalNamespace: response.external_namespace || '',
    robotUsername: response.robot_username || '',
    visibility: VALID_VISIBILITIES.includes(response.visibility as Visibility)
      ? (response.visibility as Visibility)
      : 'private',
    repositoryFilters: (response.repository_filters || []).join(', '),
    syncStartDate: formatDateForInput(response.sync_start_date || ''),
    syncValue: value.toString(),
    syncUnit: VALID_SYNC_UNITS.includes(unit as SyncUnit)
      ? (unit as SyncUnit)
      : 'hours',
    username: response.external_registry_username || '',
    password: '', // Don't populate password for security
    verifyTls: response.external_registry_config?.verify_tls ?? true,
    httpProxy: response.external_registry_config?.proxy?.http_proxy || '',
    httpsProxy: response.external_registry_config?.proxy?.https_proxy || '',
    noProxy: response.external_registry_config?.proxy?.no_proxy || '',
    skopeoTimeout: response.skopeo_timeout || 300,
  };
};

export const useOrgMirroringConfig = (
  orgName: string,
  reset: (data: OrgMirroringFormData) => void,
  setSelectedRobot: (robot: Entity | null) => void,
) => {
  const queryClient = useQueryClient();

  // Track whether we've already populated the form from fetched data,
  // so we don't overwrite user edits on background refetches.
  const hasPopulatedForm = useRef(false);

  const {
    data: config = null,
    isLoading,
    error: queryError,
  } = useQuery<OrgMirrorConfig | null>({
    queryKey: [ORG_MIRROR_QUERY_KEY, orgName],
    queryFn: async () => {
      try {
        return await getOrgMirrorConfig(orgName);
      } catch (err: unknown) {
        if (isAxiosError(err) && err.response?.status === 404) {
          return null;
        }
        throw err;
      }
    },
  });

  const error = queryError
    ? (queryError as Error).message ||
      'Failed to load organization mirror configuration'
    : null;

  // Populate form once when config data first arrives
  useEffect(() => {
    if (config && !hasPopulatedForm.current) {
      hasPopulatedForm.current = true;
      reset(configToFormData(config));

      if (config.robot_username) {
        const isRobot = config.robot_username.includes('+');
        const robotEntity: Entity = {
          name: config.robot_username,
          is_robot: isRobot,
          kind: EntityKind.user,
          is_org_member: true,
        };
        setSelectedRobot(robotEntity);
      }
    }
  }, [config, reset, setSelectedRobot]);

  // Allow manual config override (e.g. after delete)
  const setConfig = useCallback(
    (newConfig: OrgMirrorConfig | null) => {
      queryClient.setQueryData([ORG_MIRROR_QUERY_KEY, orgName], newConfig);
      if (newConfig === null) {
        hasPopulatedForm.current = false;
      }
    },
    [queryClient, orgName],
  );

  const invalidateConfig = useCallback(() => {
    hasPopulatedForm.current = false;
    queryClient.invalidateQueries({queryKey: [ORG_MIRROR_QUERY_KEY, orgName]});
  }, [queryClient, orgName]);

  // Submit configuration (create or update)
  const submitConfig = useCallback(
    async (data: OrgMirroringFormData) => {
      const filters = data.repositoryFilters
        .split(',')
        .map((f) => f.trim())
        .filter((f) => f.length > 0);

      const syncInterval = convertToSeconds(
        Number(data.syncValue),
        data.syncUnit,
      );

      const syncStartDate = (
        data.syncStartDate
          ? new Date(data.syncStartDate).toISOString()
          : new Date().toISOString()
      ).replace(/\.\d{3}Z$/, 'Z');

      const mirrorConfig: CreateOrgMirrorConfig = {
        external_registry_type: data.externalRegistryType,
        external_registry_url: data.externalRegistryUrl,
        external_namespace: data.externalNamespace,
        robot_username: data.robotUsername,
        visibility: data.visibility,
        sync_interval: syncInterval,
        sync_start_date: syncStartDate,
        is_enabled: data.isEnabled,
        external_registry_config: {
          verify_tls: data.verifyTls,
          proxy: {
            http_proxy: data.httpProxy || null,
            https_proxy: data.httpsProxy || null,
            no_proxy: data.noProxy || null,
          },
        },
        repository_filters: filters,
        skopeo_timeout: data.skopeoTimeout,
      };

      // Credentials handling:
      // - On create: always include both fields
      // - On update: always include username if present, only include
      //   password when the user actually entered a new value
      const existingHasCredentials = config?.external_registry_username != null;
      if (!config) {
        mirrorConfig.external_registry_username = data.username || null;
        mirrorConfig.external_registry_password = data.password || null;
      } else {
        if (data.username || existingHasCredentials) {
          mirrorConfig.external_registry_username = data.username || null;
        }
        if (data.password) {
          mirrorConfig.external_registry_password = data.password;
        }
      }

      if (config) {
        const {external_registry_type: _, ...updatePayload} = mirrorConfig;
        await updateOrgMirrorConfig(orgName, updatePayload);
      } else {
        await createOrgMirrorConfig(orgName, mirrorConfig);
      }

      // Refresh config from server after save
      invalidateConfig();
    },
    [config, orgName, invalidateConfig],
  );

  // Sync now operation
  const [isSyncingNow, setIsSyncingNow] = useState(false);
  const handleSyncNow = useCallback(async () => {
    setIsSyncingNow(true);
    try {
      await syncOrgMirrorNow(orgName);
      invalidateConfig();
    } finally {
      setIsSyncingNow(false);
    }
  }, [orgName, invalidateConfig]);

  // Cancel sync operation
  const handleCancelSync = useCallback(async () => {
    await cancelOrgMirrorSync(orgName);
    invalidateConfig();
  }, [orgName, invalidateConfig]);

  // Verify connection operation
  const [isVerifying, setIsVerifying] = useState(false);
  const handleVerifyConnection = useCallback(async () => {
    setIsVerifying(true);
    try {
      return await verifyOrgMirrorConnection(orgName);
    } finally {
      setIsVerifying(false);
    }
  }, [orgName]);

  // Toggle enabled operation
  const handleToggleEnabled = useCallback(
    async (checked: boolean) => {
      await updateOrgMirrorConfig(orgName, {is_enabled: checked});
      invalidateConfig();
    },
    [orgName, invalidateConfig],
  );

  return {
    config,
    setConfig,
    isLoading,
    error,
    submitConfig,
    invalidateConfig,
    // Sync operations
    isSyncingNow,
    handleSyncNow,
    handleCancelSync,
    isVerifying,
    handleVerifyConnection,
    handleToggleEnabled,
  };
};
