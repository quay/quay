var urlParseURL = require('url-parse');

/**
 * Service which exposes the server-defined API as a nice set of helper methods and automatic
 * callbacks. Any method defined on the server is exposed here as an equivalent method. Also
 * defines some helper functions for working with API responses.
 */
angular.module('quay').factory('ApiService', ['Restangular', '$q', 'UtilService', function(Restangular, $q, UtilService) {
  var apiService = {};

  var getResource = function(getMethod, operation, opt_parameters, opt_background) {
    var resource = {};
    var paginationKey = null;

    resource.withOptions = function(options) {
      this.options = options;
      return this;
    };

    resource.withPagination = function(key) {
      paginationKey = key;
      return this;
    };

    resource.get = function(processor, opt_errorHandler) {
      var options = this.options;
      var result = {
        'loading': true,
        'value': null,
        'hasError': false
      };

      var paginatedResults = [];

      var performGet = function(opt_nextPageToken) {
        if (opt_nextPageToken) {
          opt_parameters = opt_parameters || {};
          opt_parameters['next_page'] = opt_nextPageToken;
        }

        getMethod(options, opt_parameters, opt_background, true).then(function(resp) {
          if (paginationKey) {
            if (resp && resp[paginationKey]) {
              Array.prototype.push.apply(paginatedResults, resp[paginationKey]);

              var fullResp = {};
              fullResp[paginationKey] = paginatedResults;
              result.value = processor(fullResp);
              result.loading = resp['next_page'] != null;

              if (result.loading) {
                performGet(resp['next_page']);
              }

              return;
            }
          }

          result.value = processor(resp);
          result.loading = false;
        }, function(resp) {
          result.hasError = true;
          result.loading = false;
          if (opt_errorHandler) {
            opt_errorHandler(resp);
          }
        });
      };

      performGet();
      return result;
    };

    return resource;
  };

  var buildUrl = function(path, parameters) {
    // We already have /api/v1/ on the URLs, so remove them from the paths.
    path = path.substr('/api/v1/'.length, path.length);

    // Build the path, adjusted with the inline parameters.
    var used = {};
    var urlPath = '';
    for (var i = 0; i < path.length; ++i) {
      var c = path[i];
      if (c == '{') {
        var end = path.indexOf('}', i);
        var varName = path.substr(i + 1, end - i - 1);

        if (!parameters[varName]) {
          throw new Error('Missing parameter: ' + varName);
        }

        used[varName] = true;
        urlPath += encodeURI(parameters[varName]);
        i = end;
        continue;
      }

      urlPath += c;
    }

    // Append any query parameters.
    var url = new urlParseURL(urlPath, '/');
    url.query = {};

    for (var paramName in parameters) {
      if (!parameters.hasOwnProperty(paramName)) { continue; }
      if (used[paramName]) { continue; }

      var value = parameters[paramName];
      if (value != null) {
        url.query[paramName] = value
      }
    }

    return url.toString();
  };

  var getGenericOperationName = function(userOperationName) {
    return userOperationName.replace('User', '');
  };

  var getMatchingUserOperationName = function(orgOperationName, method, userRelatedResource) {
    if (userRelatedResource) {
      if (userRelatedResource[method.toLowerCase()]) {
        return userRelatedResource[method.toLowerCase()]['operationId'];
      }
    }

    throw new Error('Could not find user operation matching org operation: ' + orgOperationName);
  };

  var freshLoginInProgress = [];
  var reject = function(msg) {
    for (var i = 0; i < freshLoginInProgress.length; ++i) {
      freshLoginInProgress[i].deferred.reject({'data': {'message': msg}});
    }
    freshLoginInProgress = [];
  };

  var retry = function() {
    for (var i = 0; i < freshLoginInProgress.length; ++i) {
      freshLoginInProgress[i].retry();
    }
    freshLoginInProgress = [];
  };

  var freshLoginFailCheck = function(opName, opArgs) {
    return function(resp) {
      var deferred = $q.defer();

      // If the error is a fresh login required, show the dialog.
      // TODO: remove error_type (old style error)
      var fresh_login_required = resp.data['title'] == 'fresh_login_required' || resp.data['error_type'] == 'fresh_login_required';
      if (resp.status == 401 && fresh_login_required) {
        var retryOperation = function() {
          apiService[opName].apply(apiService, opArgs).then(function(resp) {
            deferred.resolve(resp);
          }, function(resp) {
            deferred.reject(resp);
          });
        };

        var verifyNow = function() {
          if (!$('#freshPassword').val()) {
            return;
          }

          var info = {
            'password': $('#freshPassword').val()
          };

          $('#freshPassword').val('');

          // Conduct the sign in of the user.
          apiService.verifyUser(info).then(function() {
            // On success, retry the operations. if it succeeds, then resolve the
            // deferred promise with the result. Otherwise, reject the same.
            retry();
          }, function(resp) {
            // Reject with the sign in error.
            reject('Invalid verification credentials');
          });
        };

        // Add the retry call to the in progress list. If there is more than a single
        // in progress call, we skip showing the dialog (since it has already been
        // shown).
        freshLoginInProgress.push({
          'deferred': deferred,
          'retry': retryOperation
        })

        if (freshLoginInProgress.length > 1) {
          return deferred.promise;
        }

        var box = bootbox.dialog({
          "message": 'It has been more than a few minutes since you last logged in, ' +
            'so please verify your password to perform this sensitive operation:' +
            '<form style="margin-top: 10px" action="javascript:$(\'.btn-continue\').click();void(0)">' +
            '<input id="freshPassword" class="form-control" type="password" placeholder="Current Password">' +
            '</form>',
          "title": 'Please Verify',
          "buttons": {
            "verify": {
              "label": "Verify",
              "className": "btn-success btn-continue",
              "callback": verifyNow
            },
            "close": {
              "label": "Cancel",
              "className": "btn-default",
              "callback": function() {
                reject('Verification canceled')
              }
            }
          }
        });

        box.bind('shown.bs.modal', function(){
          box.find("input").focus();
          box.find("form").submit(function() {
            if (!$('#freshPassword').val()) { return; }

            box.modal('hide');
            verifyNow();
          });
        });

        // Return a new promise. We'll accept or reject it based on the result
        // of the login.
        return deferred.promise;
      }

      // Otherwise, we just 'raise' the error via the reject method on the promise.
      return $q.reject(resp);
    };
  };

  var buildMethodsForOperation = function(operation, method, path, resourceMap) {
    var operationName = operation['operationId'];
    var urlPath = path['x-path'];

    // Add the operation itself.
    apiService[operationName] = function(opt_options, opt_parameters, opt_background, opt_forceget) {
      var one = Restangular.one(buildUrl(urlPath, opt_parameters));
      if (opt_background) {
        one.withHttpConfig({
          'ignoreLoadingBar': true
        });
      }

      var opObj = one[opt_forceget ? 'get' : 'custom' + method.toUpperCase()](opt_options);

      // If the operation requires_fresh_login, then add a specialized error handler that
      // will defer the operation's result if sudo is requested.
      if (operation['x-requires-fresh-login']) {
        opObj = opObj.catch(freshLoginFailCheck(operationName, arguments));
      }
      return opObj;
    };

    // If the method for the operation is a GET, add an operationAsResource method.
    if (method == 'get') {
      apiService[operationName + 'AsResource'] = function(opt_parameters, opt_background) {
        var getMethod = apiService[operationName];
        return getResource(getMethod, operation, opt_parameters, opt_background);
      };
    }

    // If the operation has a user-related operation, then make a generic operation for this operation
    // that can call both the user and the organization versions of the operation, depending on the
    // parameters given.
    if (path['x-user-related']) {
      var userOperationName = getMatchingUserOperationName(operationName, method, resourceMap[path['x-user-related']]);
      var genericOperationName = getGenericOperationName(userOperationName);
      apiService[genericOperationName] = function(orgname, opt_options, opt_parameters, opt_background) {
        if (orgname) {
          if (orgname.name) {
            orgname = orgname.name;
          }

          var params = jQuery.extend({'orgname' : orgname}, opt_parameters || {}, opt_background);
          return apiService[operationName](opt_options, params);
        } else {
          return apiService[userOperationName](opt_options, opt_parameters, opt_background);
        }
      };
    }
  };

  if (!window.__endpoints) {
    return apiService;
  }

  var allowedMethods = ['get', 'post', 'put', 'delete'];
  var resourceMap = {};
  var forEachOperation = function(callback) {
    for (var path in window.__endpoints) {
      if (!window.__endpoints.hasOwnProperty(path)) {
        continue;
      }

      for (var method in window.__endpoints[path]) {
        if (!window.__endpoints[path].hasOwnProperty(method)) {
          continue;
        }

        if (allowedMethods.indexOf(method.toLowerCase()) < 0) { continue; }
        callback(window.__endpoints[path][method], method, window.__endpoints[path]);
      }
    }
  };

  // Build the map of resource names to their objects.
  forEachOperation(function(operation, method, path) {
    resourceMap[path['x-name']] = path;
  });

  // Construct the methods for each API endpoint.
  forEachOperation(function(operation, method, path) {
    buildMethodsForOperation(operation, method, path, resourceMap);
  });

  apiService.getErrorMessage = function(resp, defaultMessage) {
    var message = defaultMessage;
    if (resp && resp['data']) {
      //TODO: remove error_message and error_description (old style error)
      message = resp['data']['detail'] || resp['data']['error_message'] || resp['data']['message'] || resp['data']['error_description'] || message;
    }

    return message;
  };

  apiService.errorDisplay = function(defaultMessage, opt_handler) {
    return function(resp) {
      var message = apiService.getErrorMessage(resp, defaultMessage);
      if (opt_handler) {
        var handlerMessage = opt_handler(resp);
        if (handlerMessage) {
          message = handlerMessage;
        }
      }

      message = UtilService.stringToHTML(message);
      bootbox.dialog({
        "message": message,
        "title": defaultMessage || 'Request Failure',
        "buttons": {
          "close": {
            "label": "Close",
            "className": "btn-primary"
          }
        }
      });
    };
  };

  return apiService;
}]);
