/**
 * Regular expression filter.
 */
angular.module('quay').filter('regex', function() {
  return function(input, regex) {
    if (!regex) { return []; }

    try {
      var patt = new RegExp(regex);
    } catch (ex) {
      return [];
    }

    var out = [];
    for (var i = 0; i < input.length; ++i){
      var m = input[i].match(patt);
      if (m && m[0].length == input[i].length) {
        out.push(input[i]);
      }
    }
    return out;
  };
});
