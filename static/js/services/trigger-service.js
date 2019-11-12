/**
 * Helper service for defining the various kinds of build triggers and retrieving information
 * about them.
 */
angular.module('quay').factory('TriggerService', ['UtilService', '$sanitize', 'KeyService', 'Features', 'CookieService', 'Config',
    function(UtilService, $sanitize, KeyService, Features, CookieService, Config) {
  var triggerService = {};

  var branch_tag = {
    'title': 'Branch/Tag',
    'type': 'autocomplete',
    'name': 'refs',
    'iconMap': {
      'branch': 'fa-code-fork',
      'tag': 'fa-tag'
    }
  };

  var triggerTypes = {
    'github': {
      'run_parameters': [branch_tag],
      'get_redirect_url': function(namespace, repository) {
        var redirect_uri = KeyService['githubRedirectUri'] + '/trigger/' +
          namespace + '/' + repository;

        var client_id = KeyService['githubTriggerClientId'];

        var authorize_url = new UtilService.UrlBuilder(KeyService['githubTriggerAuthorizeUrl']);
        authorize_url.setQueryParameter('client_id', client_id);
        authorize_url.setQueryParameter('scope', 'repo,user:email');
        authorize_url.setQueryParameter('redirect_uri', redirect_uri);
        return authorize_url.toString();
      },
      'is_external': true,
      'is_enabled': function() {
        return Features.GITHUB_BUILD;
      },
      'icon': 'fa-github',
      'title': function() {
        var isEnterprise = KeyService.isEnterprise('github-trigger');
        if (isEnterprise) {
          return 'GitHub Enterprise Repository Push';
        }

        return 'GitHub Repository Push';
      },
      'supports_full_directory_listing': true,
      'templates': {
        'credentials': '/static/directives/trigger/githost/credentials.html',
        'trigger-description': '/static/directives/trigger/github/trigger-description.html'
      },
      'link_templates': {
        'commit': '/commit/{sha}',
        'branch': '/tree/{branch}',
        'tag': '/releases/tag/{tag}',
      }
    },

    'bitbucket': {
      'run_parameters': [branch_tag],
      'get_redirect_url': function(namespace, repository) {
        return Config.getUrl('/bitbucket/setup/' + namespace + '/' + repository);
      },
      'is_external': false,
      'is_enabled': function() {
        return Features.BITBUCKET_BUILD;
      },
      'icon': 'fa-bitbucket',
      'title': function() { return 'Bitbucket Repository Push'; },
      'supports_full_directory_listing': false,
      'templates': {
        'credentials': '/static/directives/trigger/githost/credentials.html',
        'trigger-description': '/static/directives/trigger/bitbucket/trigger-description.html'
      },
      'link_templates': {
        'commit': '/commits/{sha}',
        'branch': '/branch/{branch}',
        'tag': '/commits/tag/{tag}',
      }
    },

    'gitlab': {
      'run_parameters': [branch_tag],
      'get_redirect_url': function(namespace, repository) {
        var redirect_uri = KeyService['gitlabRedirectUri'] + '/trigger';
        var client_id = KeyService['gitlabTriggerClientId'];

        var authorize_url = new UtilService.UrlBuilder(KeyService['gitlabTriggerAuthorizeUrl']);
        authorize_url.setQueryParameter('client_id', client_id);
        authorize_url.setQueryParameter('state', 'repo:' + namespace + '/' + repository);
        authorize_url.setQueryParameter('redirect_uri', redirect_uri);
        authorize_url.setQueryParameter('response_type', 'code');
        return authorize_url.toString();
      },
      'is_external': false,
      'is_enabled': function() {
        return Features.GITLAB_BUILD;
      },
      'icon': 'fa-gitlab',
      'title': function() { return 'GitLab Repository Push'; },
      'supports_full_directory_listing': false,
      'templates': {
        'credentials': '/static/directives/trigger/githost/credentials.html',
        'trigger-description': '/static/directives/trigger/gitlab/trigger-description.html'
      },
      'link_templates': {
        'commit': '/commit/{sha}',
        'branch': '/tree/{branch}',
        'tag': '/commits/{tag}',
      }
    },

    'custom-git': {
      'run_parameters': [
        {
          'title': 'Commit',
          'type': 'regex',
          'name': 'commit_sha',
          'regex': '^([A-Fa-f0-9]{7,})$',
          'placeholder': '1c002dd'
        }
      ],
      'get_redirect_url': function(namespace, repository) {
        return Config.getUrl('/customtrigger/setup/' + namespace + '/' + repository);
      },
      'is_external': false,
      'is_enabled': function() { return true; },
      'icon': 'fa-git-square',
      'title': function() { return 'Custom Git Repository Push'; },
      'templates': {
        'credentials': '/static/directives/trigger/custom-git/credentials.html',
        'trigger-description': '/static/directives/trigger/custom-git/trigger-description.html'
      }
    }
  };

  triggerService.populateTemplate = function(scope, name) {
    scope.$watch('trigger', function(trigger) {
      if (!trigger) { return; }
      scope.triggerTemplate = triggerService.getTemplate(trigger.service, name);
    });
  };

  triggerService.getCommitUrl = function(build) {
    // Check for a predefined URL first.
    if (build.trigger_metadata && build.trigger_metadata.commit_info &&
        build.trigger_metadata.commit_info.url) {
      return build.trigger_metadata.commit_info.url;
    }

    return triggerService.getFullLinkTemplate(build, 'commit')
                         .replace('{sha}', triggerService.getCommitSHA(build.trigger_metadata))
  };

  triggerService.getFullLinkTemplate = function(build, templateName) {
    if (!build.trigger) {
      return null;
    }

    var type = triggerTypes[build.trigger.service];
    if (!type) {
      return null;
    }

    var repositoryUrl = build.trigger.repository_url;
    if (!repositoryUrl) {
      return null;
    }

    var linkTemplate = type.link_templates;
    if (!linkTemplate || !linkTemplate[templateName]) {
      return null;
    }

    return repositoryUrl + linkTemplate[templateName];
  };

  triggerService.supportsFullListing = function(name) {
    var type = triggerTypes[name];
    if (!type) {
      return false;
    }

    return !!type['supports_full_directory_listing'];
  };

  triggerService.getTypes = function() {
    var types = [];
    for (var key in triggerTypes) {
      if (!triggerTypes.hasOwnProperty(key)) {
        continue;
      }
      types.push(key);
    }
    return types;
  };

  triggerService.getTemplate = function(name, template) {
    var type = triggerTypes[name];
    if (!type) {
      return '';
    }
    return type['templates'][template];
  };

  triggerService.getRedirectUrl = function(name, namespace, repository) {
    var type = triggerTypes[name];
    if (!type) {
      return '';
    }
    return type['get_redirect_url'](namespace, repository);
  };

  triggerService.getDockerfileLocation = function(trigger) {
    var subdirectory = trigger.config.subdir;
    if (!subdirectory) {
      return '//Dockerfile';
    }

    return '//' + subdirectory.replace(new RegExp('(^\/+|\/+$)'), '') + 'Dockerfile';
  };

  triggerService.isEnabled = function(name) {
    var type = triggerTypes[name];
    if (!type) {
      return false;
    }
    return type['is_enabled']();
  };

  triggerService.getIcon = function(name) {
    var type = triggerTypes[name];
    if (!type) {
      return 'Unknown';
    }
    return type['icon'];
  };

  triggerService.getTitle = function(name) {
    var type = triggerTypes[name];
    if (!type) {
      return 'Unknown';
    }
    return type['title']();
  };

  triggerService.getDescription = function(name, config) {
    var icon = triggerService.getIcon(name);
    var title = triggerService.getTitle(name);
    var source = '';
    if (config && config['build_source']) {
      source = UtilService.textToSafeHtml(config['build_source']);
    }

    var desc = '<i class"fa ' + icon + ' fa-lg" style="margin-left:2px; margin-right: 2px"></i> Push to ' + title + ' ' + source;
    return desc;
  };

  triggerService.getCommitSHA = function(metadata) {
    return metadata.commit || metadata.commit_sha;
  };

  triggerService.getMetadata = function(name) {
    return triggerTypes[name];
  };

  triggerService.getRunParameters = function(name, config) {
    var type = triggerTypes[name];
    if (!type) {
      return [];
    }
    return type['run_parameters'];
  }

  return triggerService;
}]);
