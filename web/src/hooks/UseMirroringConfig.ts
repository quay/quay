import {useState, useEffect} from 'react';
import {
  MirroringConfigResponse,
  getMirrorConfig,
  createMirrorConfig,
  updateMirrorConfig,
} from 'src/resources/MirroringResource';
import {MirroringFormData} from 'src/routes/RepositoryDetails/Mirroring/types';
import {
  convertToSeconds,
  convertFromSeconds,
  formatDateForInput,
} from 'src/libs/utils';
import {
  timestampToISO,
  timestampFromISO,
} from 'src/resources/MirroringResource';
import {Entity, EntityKind} from 'src/resources/UserResource';

export const useMirroringConfig = (
  namespace: string,
  repoName: string,
  repoState: string | undefined,
  reset: (data: MirroringFormData) => void,
  setSelectedRobot: (robot: Entity | null) => void,
) => {
  const [config, setConfig] = useState<MirroringConfigResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load existing configuration
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setIsLoading(true);
        const response = await getMirrorConfig(namespace, repoName);
        setConfig(response);

        // Populate form with existing values
        const {value, unit} = convertFromSeconds(response.sync_interval);

        reset({
          isEnabled: response.is_enabled,
          externalReference: response.external_reference || '',
          tags: response.root_rule.rule_value.join(', '),
          syncStartDate: formatDateForInput(response.sync_start_date || ''),
          syncValue: value.toString(),
          syncUnit: unit,
          robotUsername: response.robot_username || '',
          username: response.external_registry_username || '',
          password: '', // Don't populate password for security
          verifyTls: response.external_registry_config?.verify_tls ?? true,
          httpProxy: response.external_registry_config?.proxy?.http_proxy || '',
          httpsProxy:
            response.external_registry_config?.proxy?.https_proxy || '',
          noProxy: response.external_registry_config?.proxy?.no_proxy || '',
          unsignedImages:
            response.external_registry_config?.unsigned_images ?? false,
        });

        // Set selected robot if there's one configured
        if (response.robot_username) {
          const robotEntity: Entity = {
            name: response.robot_username,
            is_robot: response.robot_username.includes('+'),
            kind: response.robot_username.includes('+')
              ? EntityKind.user
              : EntityKind.team,
            is_org_member: true,
          };
          setSelectedRobot(robotEntity);
        }
      } catch (error: unknown) {
        if (
          (error as {response?: {status?: number}}).response?.status === 404
        ) {
          setConfig(null);
        } else {
          setError(
            (error as Error).message || 'Failed to load mirror configuration',
          );
        }
      } finally {
        setIsLoading(false);
      }
    };

    if (repoState === 'MIRROR') {
      fetchConfig();
    } else {
      setIsLoading(false);
    }
  }, [namespace, repoName, repoState, reset, setSelectedRobot]);

  // Submit configuration
  const submitConfig = async (data: MirroringFormData) => {
    // Split and clean up tags to match backend expectation
    const tagPatterns = data.tags
      .split(',')
      .map((tag) => tag.trim())
      .filter((tag) => tag.length > 0);

    const mirrorConfig = {
      is_enabled: data.isEnabled,
      external_reference: data.externalReference,
      external_registry_username: data.username || null,
      external_registry_password: data.password || null,
      sync_start_date: timestampToISO(timestampFromISO(data.syncStartDate)),
      sync_interval: convertToSeconds(Number(data.syncValue), data.syncUnit),
      robot_username: data.robotUsername,
      external_registry_config: {
        verify_tls: data.verifyTls,
        unsigned_images: data.unsignedImages,
        proxy: {
          http_proxy: data.httpProxy || null,
          https_proxy: data.httpsProxy || null,
          no_proxy: data.noProxy || null,
        },
      },
      root_rule: {
        rule_kind: 'tag_glob_csv',
        rule_value: tagPatterns,
      },
    };

    if (config) {
      await updateMirrorConfig(namespace, repoName, mirrorConfig);
    } else {
      await createMirrorConfig(namespace, repoName, mirrorConfig);
    }
  };

  return {
    config,
    setConfig,
    isLoading,
    error,
    setError,
    submitConfig,
  };
};
