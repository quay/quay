/**
 * Service for building strings, with wildcards replaced with metadata.
 */
angular.module('quay').factory('StringBuilderService', ['$sce', 'UtilService', function($sce, UtilService) {
  var stringBuilderService = {};

  var fieldIcons = {
    'inviter': 'user',
    'username': 'user',
    'user': 'user',
    'email': 'envelope',
    'activating_username': 'user',
    'delegate_user': 'user',
    'delegate_team': 'group',
    'team': 'group',
    'token': 'key',
    'repo': 'hdd-o',
    'robot': 'ci-robot',
    'tag': 'tag',
    'tags': 'tag',
    'role': 'th-large',
    'original_role': 'th-large',
    'application_name': 'cloud',
    'image': 'archive',
    'original_image': 'archive',
    'client_id': 'chain',
    'manifest_digest': 'link'
  };

  var allowMarkdown = {
    'description': true,
  };

  var filters = {
    'obj': function(value) {
      if (!value) { return []; }
      return Object.getOwnPropertyNames(value);
    },

    'updated_tags': function(value) {
      if (!value) { return []; }
      return value.join(', ');
    },

    'kid': function(kid, metadata) {
      if (metadata.name) {
        return metadata.name;
      }

      return metadata.kid.substr(0, 12);
    },

    'created_date': function(value) {
      return moment.unix(value).format('LLL');
    },

    'expiration_date': function(value) {
      return moment.unix(value).format('LLL');
    },

    'old_expiration_date': function(value) {
      return moment.unix(value).format('LLL');
    }
  };

  stringBuilderService.buildUrl = function(value_or_func, metadata) {
    var url = value_or_func;
    if (typeof url != 'string') {
      url = url(metadata);
    }

    // Find the variables to be replaced.
    var varNames = [];
    for (var i = 0; i < url.length; ++i) {
      var c = url[i];
      if (c == '{') {
        for (var j = i + 1; j < url.length; ++j) {
          var d = url[j];
          if (d == '}') {
            varNames.push(url.substring(i + 1, j));
            i = j;
            break;
          }
        }
      }
    }

    // Replace all variables found.
    for (var i = 0; i < varNames.length; ++i) {
      var varName = varNames[i];
      if (!metadata[varName]) {
        return null;
      }

      url = url.replace('{' + varName + '}', metadata[varName]);
    }

    return url;
  };

  stringBuilderService.buildTrustedString = function(value_or_func, metadata, opt_codetag) {
    return $sce.trustAsHtml(stringBuilderService.buildString(value_or_func, metadata, opt_codetag));
  };

  stringBuilderService.replaceField = function(description, prefix, key, value, opt_codetag) {
    if (Array.isArray(value)) {
      value = value.join(', ');
    } else if (typeof value == 'object') {
      for (var subkey in value) {
        if (value.hasOwnProperty(subkey)) {
          description = stringBuilderService.replaceField(description, prefix + key + '.',
            subkey, value[subkey], opt_codetag)
        }
      }

      return description
    }

    var safe = UtilService.textToSafeHtml(value.toString());
    var safeHtml = safe;
    if (allowMarkdown[key]) {
      safeHtml = UtilService.getMarkedDown(safeHtml);
      safeHtml = safeHtml.substr('<p>'.length, safeHtml.length - '<p></p>'.length);
    }

    var icon = fieldIcons[key];
    if (icon) {
      if (icon.indexOf('ci-') < 0) {
        icon = 'fa-' + icon;
      }

      safeHtml = `<i class="fa ${icon}"></i>${safeHtml}`;
    }

    var codeTag = opt_codetag || 'code';
    var tagKey = prefix + key;
    description = description.replace(`{${tagKey}}`,
      `<${codeTag} class="tag-${tagKey}" title="${safe}">${safeHtml}</${codeTag}>`);

    return description
  }

  stringBuilderService.buildString = function(value_or_func, metadata, opt_codetag, opt_summarize) {
    var description = value_or_func;
    if (typeof description != 'string') {
      description = description(metadata);
    }

    if (opt_summarize) {
      // Remove any summary text.
      description = description.replace(/\[\[([^\]])+\]\]/g, '');
    } else {
      // Remove summary text placeholders.
      description = description.replace(/\[\[/g, '');
      description = description.replace(/\]\]/g, '');
    }

    for (var key in metadata) {
      if (metadata.hasOwnProperty(key)) {
        var value = metadata[key] != null ? metadata[key] : '(Unknown)';
        if (filters[key]) {
          value = filters[key](value, metadata);
        }

        description = stringBuilderService.replaceField(description, '', key, value, opt_codetag);
      }
    }
    return description.replace(/(\r\n|\n|\r)/gm, '<br>');
  };

  return stringBuilderService;
}]);
