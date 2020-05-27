import { ViewArrayImpl } from "./services/view-array/view-array.impl";
import { RegexMatchViewComponent } from "./directives/ui/regex-match-view/regex-match-view.component";
import { NgModule } from 'ng-metadata/core';
import { QuayRoutesModule } from "./quay-routes.module";
import { DockerfilePathSelectComponent } from './directives/ui/dockerfile-path-select/dockerfile-path-select.component';
import { ContextPathSelectComponent } from './directives/ui/context-path-select/context-path-select.component';
import { LinearWorkflowComponent } from './directives/ui/linear-workflow/linear-workflow.component';
import { LinearWorkflowSectionComponent } from './directives/ui/linear-workflow/linear-workflow-section.component';
import { QuayConfigModule } from './quay-config.module';
import { AppPublicViewComponent } from './directives/ui/app-public-view/app-public-view.component';
import { VisibilityIndicatorComponent } from './directives/ui/visibility-indicator/visibility-indicator.component';
import { CorTableComponent } from './directives/ui/cor-table/cor-table.component';
import { CorTableColumn } from './directives/ui/cor-table/cor-table-col.component';
import { ChannelIconComponent } from './directives/ui/channel-icon/channel-icon.component';
import { TagSigningDisplayComponent } from './directives/ui/tag-signing-display/tag-signing-display.component';
import {
  RepositorySigningConfigComponent
} from './directives/ui/repository-signing-config/repository-signing-config.component';
import { TimeMachineSettingsComponent } from './directives/ui/time-machine-settings/time-machine-settings.component';
import { DurationInputComponent } from './directives/ui/duration-input/duration-input.component';
import { SearchBoxComponent } from './directives/ui/search-box/search-box.component';
import { TypeaheadDirective } from './directives/ui/typeahead/typeahead.directive';
import { BuildServiceImpl } from './services/build/build.service.impl';
import { AvatarServiceImpl } from './services/avatar/avatar.service.impl';
import { DocumentationServiceImpl } from './services/documentation/documentation.service.impl';
import { DockerfileServiceImpl } from './services/dockerfile/dockerfile.service.impl';
import { DataFileServiceImpl } from './services/datafile/datafile.service.impl';
import { QuayRequireDirective } from './directives/structural/quay-require/quay-require.directive';
import { MarkdownInputComponent } from './directives/ui/markdown/markdown-input.component';
import { MarkdownViewComponent } from './directives/ui/markdown/markdown-view.component';
import { MarkdownToolbarComponent } from './directives/ui/markdown/markdown-toolbar.component';
import { MarkdownEditorComponent } from './directives/ui/markdown/markdown-editor.component';
import { DockerfileCommandComponent } from './directives/ui/dockerfile-command/dockerfile-command.component';
import { ImageCommandComponent } from './directives/ui/image-command/image-command.component';
import { ExpirationStatusViewComponent } from './directives/ui/expiration-status-view/expiration-status-view.component';
import { BrowserPlatform, browserPlatform } from './constants/platform.constant';
import { ManageTriggerComponent } from './directives/ui/manage-trigger/manage-trigger.component';
import { ClipboardCopyDirective } from './directives/ui/clipboard-copy/clipboard-copy.directive';
import { CorTabsModule } from './directives/ui/cor-tabs/cor-tabs.module';
import { TriggerDescriptionComponent } from './directives/ui/trigger-description/trigger-description.component';
import { TimeAgoComponent } from './directives/ui/time-ago/time-ago.component';
import { TimeDisplayComponent } from './directives/ui/time-display/time-display.component';
import { AppSpecificTokenManagerComponent } from './directives/ui/app-specific-token-manager/app-specific-token-manager.component';
import { ManifestLinkComponent } from './directives/ui/manifest-link/manifest-link.component';
import { ManifestSecurityView } from './directives/ui/manifest-security-view/manifest-security-view.component';
import { MarkdownModule } from './directives/ui/markdown/markdown.module';
import { RepoStateComponent } from './directives/ui/repo-state/repo-state.component';
import * as Clipboard from 'clipboard';


/**
 * Main application module.
 */
@NgModule({
  imports: [
    QuayRoutesModule,
    QuayConfigModule,
    CorTabsModule,
    MarkdownModule,
  ],
  declarations: [
    RegexMatchViewComponent,
    DockerfilePathSelectComponent,
    ContextPathSelectComponent,
    LinearWorkflowComponent,
    LinearWorkflowSectionComponent,
    AppPublicViewComponent,
    VisibilityIndicatorComponent,
    CorTableComponent,
    CorTableColumn,
    ChannelIconComponent,
    QuayRequireDirective,
    TagSigningDisplayComponent,
    RepositorySigningConfigComponent,
    TimeMachineSettingsComponent,
    DurationInputComponent,
    MarkdownInputComponent,
    MarkdownViewComponent,
    MarkdownToolbarComponent,
    MarkdownEditorComponent,
    SearchBoxComponent,
    DockerfileCommandComponent,
    ImageCommandComponent,
    TypeaheadDirective,
    ManageTriggerComponent,
    ExpirationStatusViewComponent,
    ClipboardCopyDirective,
    TriggerDescriptionComponent,
    TimeAgoComponent,
    TimeDisplayComponent,
    AppSpecificTokenManagerComponent,
    ManifestLinkComponent,
    ManifestSecurityView,
    RepoStateComponent,
  ],
  providers: [
    ViewArrayImpl,
    BuildServiceImpl,
    AvatarServiceImpl,
    DocumentationServiceImpl,
    DockerfileServiceImpl,
    DataFileServiceImpl,
    { provide: 'fileReaderFactory', useValue: () => new FileReader() },
    { provide: 'BrowserPlatform', useValue: browserPlatform },
    { provide: 'clipboardFactory', useValue: (trigger, options) => new Clipboard(trigger, options) },
  ],
})
export class QuayModule {

}
