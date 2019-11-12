<div class="dockerfile-build-dialog-element">
  <!-- Modal message dialog -->
  <div class="modal fade dockerfilebuildModal">
    <div class="co-dialog modal-dialog modal-lg">
      <div class="modal-content" ng-show="triggersResource && triggersResource.loading">
        <div class="cor-loader"></div>
      </div>

      <div class="modal-content" ng-show="!triggersResource || !triggersResource.loading">
        <div class="modal-header ahead-of-tabs">
          <button type="button" class="close" data-dismiss="modal" aria-hidden="true"
                  ng-show="!buildStarting">&times;</button>
          <h4 class="modal-title">
            Start Repository Build
          </h4>
        </div>
        <ul class="co-top-tab-bar" ng-show="triggers.length > 0">
          <li class="co-top-tab" ng-class="viewTriggers ? 'active': ''" ng-click="showTriggers(true)">Invoke Build Trigger</li>
          <li class="co-top-tab" ng-class="!viewTriggers ? 'active': ''" ng-click="showTriggers(false)">Upload Dockerfile</li>
        </ul>
        <div class="modal-body">
          <div class="co-alert co-alert-danger" ng-show="errorMessage">
            {{ errorMessage }}
          </div>

          <!-- Upload Dockerfile -->
          <div ng-show="!viewTriggers">
            <div class="dockerfile-build-form" repository="repository" is-ready="hasDockerfile"
                 ready-for-build="readyForBuild(startBuild)" reset="viewCounter"></div>
          </div>

          <!-- Start Build Trigger -->
          <div ng-show="viewTriggers">
            <p style="padding: 10px;">Manually running a build trigger provides the means for invoking a build trigger as-if
            called from the underlying service for the latest commit to a particular branch or tag.</p>

            <table class="cor-table">
              <thead>
                <tr>
                  <td>Trigger Description</td>
                  <td>Branches/Tags</td>
                  <td></td>
                </tr>
              </thead>
              <tbody>
                <tr ng-repeat="trigger in triggers">
                  <td><trigger-description trigger="trigger"></trigger-description></td>
                  <td>{{ trigger.config.branchtag_regex || 'All' }}</td>
                  <td>
                    <a href="javascript:void(0)" ng-click="runTriggerNow(trigger)"
                       ng-if="trigger.can_invoke">Run Trigger Now</a>
                    <span ng-if="!trigger.can_invoke"
                          data-title="You do not have permission to run this trigger" bs-tooltip>
                      <i class="fa fa-exclamation-triangle"></i> No permission to run
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-primary" ng-click="startBuild()"
                  ng-disabled="!hasDockerfile || buildStarting || !startBuildCallback"
                  ng-show="!viewTriggers">Start Build</button>
          <button type="button" class="btn btn-default" data-dismiss="modal"
                  ng-disabled="buildStarting">Close</button>
        </div>
      </div><!-- /.modal-content -->
    </div><!-- /.modal-dialog -->
  </div><!-- /.modal -->
  <div class="manual-trigger-build-dialog" repository="repository" counter="startTriggerCounter"
       trigger="startTrigger"
       build-started="handleBuildStarted(build)"></div>
</div>
