import { Directive, Inject, Input, AfterContentInit } from 'ng-metadata/core';


/**
 * Structural directive that adds/removes its host element if the given list of feature flags are set.
 * Utilizes the existing AngularJS ngIf directive by applying its 'link' function to the host element's properties.
 *
 * Inspired by http://stackoverflow.com/a/29010910
 */
@Directive({
  selector: '[quayRequire]',
  legacy: {
    transclude: 'element',
  }
})
export class QuayRequireDirective implements AfterContentInit {

  @Input('<quayRequire') public requiredFeatures: string[] = [];

  private ngIfDirective: ng.IDirective;

  constructor(@Inject('Features') private features: any,
              @Inject('$element') private $element: ng.IAugmentedJQuery,
              @Inject('$scope') private $scope: ng.IScope,
              @Inject('$transclude') private $transclude: ng.ITranscludeFunction,
              @Inject('ngIfDirective') ngIfDirective: ng.IDirective[]) {
    this.ngIfDirective = ngIfDirective[0];
  }

  public ngAfterContentInit(): void {
    const attrs: {[name: string]: () => boolean} = {'ngIf': () => this.features.matchesFeatures(this.requiredFeatures)};

    (<Function>this.ngIfDirective.link).apply(this.ngIfDirective,
                                              [
                                                this.$scope,
                                                this.$element,
                                                attrs,
                                                null,
                                                this.$transclude
                                              ]);
  }
}
