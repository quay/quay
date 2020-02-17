import { ViewArray } from '../services/view-array/view-array';


/**
 * A type representing local application data.
 */
export type Local = {
  contexts?: string[];
  dockerContext?: string;
  dockerfileLocations?: any;
  dockerfilePath?: string;
  hasValidContextLocation?: boolean;
  hasValidDockerfilePath?: boolean;
  maxScore?: number;
  namespaceOptions?: {
    filter: string;
    predicate: string;
    reverse: boolean;
    page: number;
  };
  namespaces?: Namespace[];
  orderedNamespaces?: ViewArray;
  orderedRepositories?: ViewArray;
  orderedRobotAccounts?: ViewArray;
  repositories?: Repository[];
  repositoryFullRefs?: {
    icon: string;
    title: string;
    value: string;
  }[];
  repositoryOptions?: {
    filter: string;
    predicate: string;
    reverse: boolean;
    page: number;
    hideStale: boolean;
  };
  repositoryRefs?: {
    kind: string;
    name: string;
  }[];
  robotAccount?: RobotAccount;
  robotOptions?: {
    filter: string;
    predicate: string;
    reverse: boolean;
    page: number;
  };
  selectedNamespace?: Namespace;
  selectedRepository?: Repository;
  triggerAnalysis?: any;
  currentTagTemplate?: string;
  triggerOptions?: {
    [key: string]: any;
  };
};


/**
 * A type representing a robot account.
 */
export type RobotAccount = {
  can_read: boolean;
  is_robot: boolean;
  kind: string;
  name: string;
};


/**
 * A type representing a Git repository.
 */
export type Repository = {
  name: string;
  description?: string;
  full_name?: string;
  has_admin_permissions?: boolean;
  last_updated?: number;
  last_updated_datetime?: Date;
  private?: boolean;
  url?: string;
  kind?: string;
  namespace?: string;
  trust_enabled?: boolean;
  tag_operations_disabled?: boolean;
};


/**
 * A type representing a repository namespace.
 */
export type Namespace = {
  avatar_url: string;
  id: string;
  personal: boolean;
  score: number;
  title: string;
  url: string;
};


/**
 * A type representing a trigger.
 */
export type Trigger = {
  id: string;
  service: string;
  is_active?: boolean;
  build_source?: string;
  can_invoke?: boolean;
  repository_url?: string;
  config?: any;
};


/**
 * A type representing a build trigger config.
 */
export type TriggerConfig = {
  build_source: string;
  dockerfile_path?: string;
  context?: string;
  branchtag_regex?: string;
  default_tag_from_ref?: boolean;
  latest_for_default_branch?: boolean;
  tag_templates?: string[];
};


/**
 * Represents a set of apostille delegations.
 */
export type ApostilleDelegationsSet = {
  delegations: {[delegationName: string]: ApostilleSignatureDocument};

  // The error that occurred, if any.
  error: string | null;
};

/**
 * Represents an apostille signature document, with extra expiration information.
 */
export type ApostilleSignatureDocument = {
  // When the signed document expires.
  expiration: string

  // Object of information for each tag.
  targets: {string: ApostilleTagDocument}
};


/**
 * An apostille document containing signatures for a tag.
 */
export type ApostilleTagDocument = {
  // The length of the document.
  length: number

  // The hashes for the tag.
  hashes: {string: string}
};


/**
 * A type representing a Markdown symbol.
 */
export type MarkdownSymbol = 'heading1'
                           | 'heading2'
                           | 'heading3'
                           | 'bold'
                           | 'italics'
                           | 'bulleted-list'
                           | 'numbered-list'
                           | 'quote'
                           | 'code'
                           | 'link'
                           | 'code';
