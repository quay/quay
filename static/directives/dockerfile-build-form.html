<div class="dockerfile-build-form-element">
  <div ng-show="state == 'starting-build'" class="starting-build">
    <div class="cor-loader-inline"></div>
    <div>Please wait while <span class="registry-name" short="true"></span> starts the build</div>
  </div>
  <div ng-show="state != 'starting-build'">
    <div class="file-upload-box"
         select-message="Please select a Dockerfile or an archive (.tar.gz or .zip) containing a Dockerfile at the root directory"
         files-cleared="handleFilesCleared()"
         files-selected="handleFilesSelected(files, callback)"
         files-validated="handleFilesValidated(uploadFiles)"
         reset="reset"></div>

    <div class="robot-permission" ng-show="privateBaseRepository && state != 'uploading-files'">
      <div class="help-text">
        <p>The selected Dockerfile contains a <code>FROM</code> that refers to private repository <strong>{{ privateBaseRepository }}</strong>.</p>
        <p>
          A robot account with read access to that repository is required for the build:
        </p>
      </div>
      <div class="entity-search" namespace="repository.namespace"
           placeholder="'Select robot account for pulling'"
           current-entity="pullEntity"
           pull-right="true"
           allowed-entities="['robot']"></div>
      <div class="co-alert co-alert-danger"
           ng-if="currentRobotHasPermission === false">
        Robot account <strong>{{ pullEntity.name }}</strong> does not have
        read permission on repository <strong>{{ privateBaseRepository }}</strong>.
      </div>
      <div ng-if="state == 'checking-bot'" style="margin-top: 10px;">
        <span class="cor-loader-inline"></span> Checking robot permissions...
      </div>
    </div>
  </div>
</div>
