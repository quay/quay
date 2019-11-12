(function(browserchrome, $) {
  var htmlTemplate = '<div class="browser-chrome-container"><div class="browser-chrome-header"><i class="fa fa-times-circle"></i> <i class="fa fa-minus-circle"></i> <i class="fa fa-plus-circle"></i><div class="browser-chrome-tab"><div class="browser-chrome-tab-wrapper"><div class="browser-chrome-tab-content"><i class="fa fa-file-alt fa-lg"></i> <span class="tab-title">Tab Title</span></div></div></div><div class="user-icon-container"><i class="fa fa-user fa-2x"></i></div></div><div class="browser-chrome-url-bar"><div class="left-controls"><i class="fa fa-arrow-left fa-lg"></i> <i class="fa fa-arrow-right fa-lg"></i> <i class="fa fa-rotate-right fa-lg"></i> </div><div class="right-controls"> <i class="fa fa-reorder fa-lg"></i></div><div class="browser-chrome-url"><span class="protocol-https" style="display: none"><i class="fa fa-lock"></i>https</span><span class="protocol-http"><i class="fa fa-file-alt"></i>http</span><span class="url-text">://google.com/</span></div></div></div>'

  browserchrome.update = function() {
    $('[data-screenshot-url]').each(function(index, element) {
      var elem = $(element);
      if (!elem.data('has-chrome')) {
        // Create chrome
        var createdHtml = $(htmlTemplate);

        // Add the new chrome to the page where the image was
        elem.replaceWith(createdHtml);

        // Add the image to the new browser chrome html
        createdHtml.append(elem);

        // Set the tab title
        var tabTitle = elem.attr('title') || elem.data('tab-title');
        createdHtml.find('.tab-title').text(tabTitle);

        // Pick the protocol and set the url
        var url = elem.data('screenshot-url');
        if (url.substring(0, 6) === 'https:') {
          createdHtml.find('.protocol-http').hide();
          createdHtml.find('.protocol-https').show();
          url = url.substring(5);
        } else {
          createdHtml.find('.protocol-http').hide();
          createdHtml.find('.protocol-https').show();
          url = url.substring(4);
        }
        createdHtml.find('.url-text').text(url);

        elem.data('has-chrome', 'true');
      }
    });
  };
}(window.browserchrome = window.browserchrome || {}, window.jQuery));