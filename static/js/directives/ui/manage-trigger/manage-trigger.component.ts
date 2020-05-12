import { Input, Output, Component, Inject, EventEmitter, OnChanges, SimpleChanges } from 'ng-metadata/core';
import * as moment from 'moment';
import { Local, Trigger, TriggerConfig, Repository, Namespace } from '../../../types/common.types';
import { ContextChangeEvent } from '../context-path-select/context-path-select.component';
import { PathChangeEvent } from '../dockerfile-path-select/dockerfile-path-select.component';
import './manage-trigger.component.css';


/**
 * A component that lets the user set up a build trigger for a public Git repository host service.
 */
@Component({
  selector: 'manage-trigger',
  templateUrl: '/static/js/directives/ui/manage-trigger/manage-trigger.component.html'
})
export class ManageTriggerComponent implements OnChanges {

  @Input('<') public githost: string = 'custom-git';
  @Input('<') public repository: Repository;
  @Input('<') public trigger: Trigger;

  @Output() public activateTrigger: EventEmitter<{ config: TriggerConfig, pull_robot?: any }> = new EventEmitter();

  public config: TriggerConfig;
  public local: Local = {
    selectedRepository: { name: '' },
    hasValidDockerfilePath: false,
    dockerfileLocations: [],
    triggerOptions: {
      'tag_templates': []
    },
    namespaceOptions: { filter: '', predicate: 'score', reverse: false, page: 0 },
    repositoryOptions: { filter: '', predicate: 'score', reverse: false, page: 0, hideStale: true },
    robotOptions: { filter: '', predicate: 'score', reverse: false, page: 0 },
    currentTagTemplate: null
  };

  private namespacesPerPage: number = 10;
  private repositoriesPerPage: number = 10;
  private robotsPerPage: number = 10;
  private namespaceTitle: string;
  private namespace: any;
  private buildSource: string;
  private githubTriggerEndpoint: string;
  private githubTriggerClientId: string;

  constructor(@Inject('ApiService') private apiService: any,
    @Inject('TableService') private tableService: any,
    @Inject('TriggerService') private triggerService: any,
    @Inject('RolesService') private rolesService: any,
    @Inject('KeyService') private keyService: any,
    @Inject('DocumentationService') private DocumentationService: any,
    @Inject('$scope') private $scope: ng.IScope) {
    this.githubTriggerEndpoint = keyService['githubTriggerEndpoint'];
    this.githubTriggerClientId = keyService['githubTriggerClientId'];
  }

  public ngOnChanges(changes: SimpleChanges): void {
    if (this.githost && this.repository && this.trigger) {
      this.config = this.trigger.config || {};
      this.namespaceTitle = 'organization';
      this.local.selectedNamespace = null;
      if (this.githost != 'custom-git') {
        this.loadNamespaces();
      }

      // FIXME (Alec 5/26/17): Need to have watchers here because cor-table doesn't have ng-change functionality yet
      this.$scope.$watch(() => this.local.selectedNamespace, (namespace: Namespace) => {
        if (namespace) {
          this.loadRepositories(namespace);
        }
      });
      this.$scope.$watch(() => this.local.selectedRepository, (selectedRepository: Repository) => {
        if (selectedRepository && this.githost != 'custom-git') {
          this.loadRepositoryRefs(selectedRepository);
          this.loadDockerfileLocations(selectedRepository);
        }
      });
    }
  }

  public getTriggerIcon(): any {
    return this.triggerService.getIcon(this.trigger.service);
  }

  public checkBuildSource(buildSource: string): void {
    const buildSourceRegExp = new RegExp(/(((http|https):\/\/)(.+)|\w+@(.+):(.+))/, 'i');
    try {
      this.local.selectedRepository.full_name = buildSourceRegExp.test(buildSource) ? buildSource : null;
    } catch (error) {
      this.local.selectedRepository.full_name = null;
    }
  }

  public checkDockerfilePath(event: PathChangeEvent): void {
    this.local.hasValidDockerfilePath = event.isValid && event.path.split('/')[event.path.split('/').length - 1] != '';
    this.local.dockerfilePath = event.path;

    if (event.path && this.local.selectedRepository) {
      this.setPossibleContexts(event.path);
      this.analyzeDockerfilePath(this.local.selectedRepository, this.local.dockerfilePath, this.local.dockerContext);
    }
  }

  public checkBuildContext(event: ContextChangeEvent): void {
    this.local.hasValidContextLocation = event.isValid;
    this.local.dockerContext = event.contextDir;

    if (event.contextDir && this.local.selectedRepository) {
      this.analyzeDockerfilePath(this.local.selectedRepository, this.local.dockerfilePath, this.local.dockerContext);
    }
  }

  public analyzeDockerfilePath(selectedRepo: Repository, path: string = '/Dockerfile', context: string = '/'): void {
    if (selectedRepo != undefined && selectedRepo.full_name) {
      this.local.triggerAnalysis = null;
      this.local.robotAccount = null;

      const params = {
        'repository': this.repository.namespace + '/' + this.repository.name,
        'trigger_uuid': this.trigger.id
      };
      const config: TriggerConfig = {
        build_source: selectedRepo.full_name,
        dockerfile_path: path.substr(1),
        context: context
      };
      const data = { config: config };

      // Try to analyze git repository, fall back to retrieving all namespace's robots
      this.apiService.analyzeBuildTrigger(data, params)
        .then((resp) => {
          if (resp['status'] === 'notimplemented') {
            return this.apiService.getRobots(this.repository.namespace, null, { 'permissions': true, 'token': false });
          } else {
            this.local.triggerAnalysis = Object.assign({}, resp);
          }
        })
        .catch((error) => {
          this.apiService.errorDisplay('Could not analyze trigger');
        })
        .then((resp) => {
          if (resp) {
            this.local.triggerAnalysis = {
              status: 'publicbase',
              is_admin: true,
              robots: resp.robots,
              name: this.repository.name,
              namespace: this.repository.namespace
            };
          }
          this.buildOrderedRobotAccounts();
        })
        .catch((error) => {
          this.apiService.errorDisplay('Could not retrieve robot accounts');
        });
    }
  }

  public createTrigger(): void {
    var config: TriggerConfig = {
      build_source: this.local.selectedRepository.full_name,
      dockerfile_path: this.local.dockerfilePath,
      context: this.local.dockerContext
    };

    if (this.local.triggerOptions['hasBranchTagFilter'] && this.local.triggerOptions['branchTagFilter']) {
      config.branchtag_regex = this.local.triggerOptions['branchTagFilter'];
    }

    config.default_tag_from_ref = this.local.triggerOptions['default_tag_from_ref'];
    config.latest_for_default_branch = this.local.triggerOptions['latest_for_default_branch'];
    config.tag_templates = this.local.triggerOptions['tag_templates'] || null;

    const activate = () => {
      this.activateTrigger.emit({ config: config, pull_robot: Object.assign({}, this.local.robotAccount) });
    };

    if (this.local.triggerAnalysis.status == 'requiresrobot' && this.local.robotAccount) {
      if (this.local.robotAccount.can_read) {
        activate();
      } else {
        // Add read permission onto the base repository for the robot and then activate the trigger.
        const baseRepo: any = { name: this.local.triggerAnalysis.name, namespace: this.local.triggerAnalysis.namespace };
        this.rolesService.setRepositoryRole(baseRepo, 'read', 'robot', this.local.robotAccount.name, activate);
      }
    } else {
      activate();
    }
  }

  private setPossibleContexts(path: string) {
    if (this.local.dockerfileLocations.contextMap) {
      this.local.contexts = this.local.dockerfileLocations.contextMap[path] || [];
    } else {
      this.local.contexts = [path.split('/').slice(0, -1).join('/').concat('/')];
    }
  }

  private buildOrderedNamespaces(): void {
    if (this.local.namespaces) {
      this.local.maxScore = 0;
      this.local.namespaces.forEach((namespace) => {
        this.local.maxScore = Math.max(namespace.score, this.local.maxScore);
      });
    }
  }

  private loadNamespaces(): void {
    this.local.namespaces = null;
    this.local.selectedNamespace = null;
    this.local.orderedNamespaces = null;

    this.local.selectedRepository = null;
    this.local.orderedRepositories = null;

    var params = {
      'repository': this.repository.namespace + '/' + this.repository.name,
      'trigger_uuid': this.trigger.id
    };

    this.apiService.listTriggerBuildSourceNamespaces(null, params)
      .then((resp) => {
        this.local.namespaces = resp['namespaces'];
        this.local.repositories = null;
        this.buildOrderedNamespaces();
      }, this.apiService.errorDisplay('Could not retrieve the list of ' + this.namespaceTitle));
  }

  private buildOrderedRepositories(): void {
    if (this.local.repositories) {
      var repositories = this.local.repositories || [];
      repositories.forEach((repository) => {
        repository['last_updated_datetime'] = new Date(repository['last_updated'] * 1000);
      });

      if (this.local.repositoryOptions.hideStale) {
        var existingRepositories = repositories;

        repositories = repositories.filter((repository) => {
          var older_date = moment(repository['last_updated_datetime']).add(1, 'months');
          return !moment().isAfter(older_date);
        });

        if (existingRepositories.length > 0 && repositories.length == 0) {
          repositories = existingRepositories;
        }
      }

      this.local.orderedRepositories = this.tableService.buildOrderedItems(repositories,
        this.local.repositoryOptions,
        ['name', 'description'],
        []);
    }
  }

  private loadRepositories(namespace: any): void {
    this.local.repositories = null;
    this.local.selectedRepository = null;
    this.local.repositoryRefs = null;
    this.local.triggerOptions = {
      'hasBranchTagFilter': false,
      'default_tag_from_ref': true,
      'latest_for_default_branch': true,
      'tag_templates': []
    };

    this.local.orderedRepositories = null;

    const params = {
      'repository': this.repository.namespace + '/' + this.repository.name,
      'trigger_uuid': this.trigger.id
    };

    const data = {
      'namespace': namespace.id
    };

    this.apiService.listTriggerBuildSources(data, params).then((resp) => {
      if (namespace == this.local.selectedNamespace) {
        this.local.repositories = resp['sources'];
        this.buildOrderedRepositories();
      }
    }, this.apiService.errorDisplay('Could not retrieve repositories'));
  }

  private addTagTemplate(): void {
    if (!this.local.currentTagTemplate) {
      return;
    }

    this.local.triggerOptions['tag_templates'].push(this.local.currentTagTemplate);
    this.local.currentTagTemplate = null;
  }

  private removeTagTemplate(template: string): void {
    var opts = this.local.triggerOptions;
    opts['tag_templates'] = opts['tag_templates'].filter(function (item) {
      return item != template;
    });
  }

  private loadRepositoryRefs(repository: any): void {
    this.local.repositoryRefs = null;
    this.local.triggerOptions = {
      'hasBranchTagFilter': false,
      'default_tag_from_ref': true,
      'latest_for_default_branch': true,
      'tag_templates': []
    };

    const params = {
      'repository': this.repository.namespace + '/' + this.repository.name,
      'trigger_uuid': this.trigger.id,
      'field_name': 'refs'
    };

    const config = {
      'build_source': repository.full_name
    };

    this.apiService.listTriggerFieldValues(config, params).then((resp) => {
      if (repository == this.local.selectedRepository) {
        this.local.repositoryRefs = resp['values'];
        this.local.repositoryFullRefs = resp['values'].map((ref) => {
          const kind = ref.kind == 'branch' ? 'heads' : 'tags';
          const icon = ref.kind == 'branch' ? 'fa-code-fork' : 'fa-tag';
          return {
            'value': `${kind}/${ref.name}`,
            'icon': icon,
            'title': ref.name
          };
        });
      }
    }, this.apiService.errorDisplay('Could not retrieve repository refs'));
  }

  private loadDockerfileLocations(repository: any): void {
    this.local.dockerfilePath = null;
    this.local.dockerContext = null;

    const params = {
      'repository': this.repository.namespace + '/' + this.repository.name,
      'trigger_uuid': this.trigger.id
    };
    const config: TriggerConfig = { build_source: repository.full_name };

    this.apiService.listBuildTriggerSubdirs(config, params)
      .then((resp) => {
        if (repository == this.local.selectedRepository) {
          this.local.dockerfileLocations = resp;
        }
      })
      .catch((error) => {
        this.apiService.errorDisplay('Could not retrieve Dockerfile locations');
      });
  }

  private buildOrderedRobotAccounts(): void {
    if (this.local.triggerAnalysis && this.local.triggerAnalysis.robots) {
      this.local.triggerAnalysis.robots = this.local.triggerAnalysis.robots.map((robot) => {
        robot.kind = robot.kind || 'user';
        robot.is_robot = robot.is_robot || true;
        return robot;
      });

      this.local.orderedRobotAccounts = this.tableService.buildOrderedItems(this.local.triggerAnalysis.robots,
        this.local.robotOptions,
        ['name'],
        []);
    }
  }
}
