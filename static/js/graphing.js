/**
 * Bind polyfill from https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Function/bind#Compatibility
 */
  if (!Function.prototype.bind) {
    Function.prototype.bind = function (oThis) {
      if (typeof this !== "function") {
        // closest thing possible to the ECMAScript 5 internal IsCallable function
        throw new TypeError("Function.prototype.bind - what is trying to be bound is not callable");
      }

      var aArgs = Array.prototype.slice.call(arguments, 1),
      fToBind = this,
      fNOP = function () {},
      fBound = function () {
        return fToBind.apply(this instanceof fNOP && oThis
                             ? this
                             : oThis,
                             aArgs.concat(Array.prototype.slice.call(arguments)));
      };

      fNOP.prototype = this.prototype;
      fBound.prototype = new fNOP();

      return fBound;
    };
  }

var DEPTH_HEIGHT = 100;
var DEPTH_WIDTH = 140;

/**
 * Based off of http://mbostock.github.io/d3/talk/20111018/tree.html by Mike Bostock (@mbostock)
 */
export function ImageHistoryTree(namespace, name, images, getTagsForImage, formatComment, formatTime,
                                 formatCommand, opt_tagFilter) {

  /**
   * The namespace of the repo.
   */
  this.repoNamespace_ = namespace;

  /**
   * The name of the repo.
   */
  this.repoName_ = name;

  /**
   * The images to display.
   */
  this.images_ = images;

  /**
   * Method to retrieve the tags for an image.
   */
  this.getTagsForImage_ = getTagsForImage;

  /**
   * Method to invoke to format a comment for an image.
   */
  this.formatComment_ = formatComment;

  /**
   * Method to invoke to format the time for an image.
   */
  this.formatTime_ = formatTime;

  /**
   * Method to invoke to format the command for an image.
   */
  this.formatCommand_ = formatCommand;

  /**
   * Method for filtering the tags and image paths displayed in the tree.
   */
  this.tagFilter_ = opt_tagFilter || function() { return true; };

  /**
   * The current tag (if any).
   */
  this.currentTag_ = null;

  /**
   * The current image (if any).
   */
  this.currentImage_ = null;

  /**
   * The currently highlighted node (if any).
   */
  this.currentNode_ = null;

  /**
   * Counter for creating unique IDs.
   */
  this.idCounter_ = 0;
}


/**
 * Calculates the dimensions of the tree.
 */
ImageHistoryTree.prototype.calculateDimensions_ = function(container) {
  var cw = document.getElementById(container).clientWidth;
  var ch = this.maxHeight_ * (DEPTH_HEIGHT + 10);

  var margin = { top: 40, right: 20, bottom: 20, left: 80 };
  var m = [margin.top, margin.right, margin.bottom, margin.left];
  var w = cw - m[1] - m[3];
  var h = ch - m[0] - m[2];

  return {
    'w': w,
    'h': h,
    'm': m,
    'cw': cw,
    'ch': ch
  };
};


ImageHistoryTree.prototype.setupOverscroll_ = function() {
  var container = this.container_;
  var that = this;
  var overscroll = $('#' + container).overscroll();

  overscroll.on('overscroll:dragstart', function() {
    $(that).trigger({
      'type': 'hideTagMenu'
    });

    $(that).trigger({
      'type': 'hideImageMenu'
    });
  });

  overscroll.on('scroll', function() {
    $(that).trigger({
      'type': 'hideTagMenu'
    });

    $(that).trigger({
      'type': 'hideImageMenu'
    });
  });
};


/**
 * Updates the dimensions of the tree.
 */
ImageHistoryTree.prototype.updateDimensions_ = function() {
  var container = this.container_;
  var dimensions = this.calculateDimensions_(container);
  if (!dimensions) { return; }

  var m = dimensions.m;
  var w = dimensions.w;
  var h = dimensions.h;
  var cw = dimensions.cw;
  var ch = dimensions.ch;

  // Set the height of the container so that it never goes offscreen.
  if (!$('#' + container).removeOverscroll) { return; }

  $('#' + container).removeOverscroll();
  var viewportHeight = $(window).height();
  var boundingBox = document.getElementById(container).getBoundingClientRect();
  document.getElementById(container).style.maxHeight = (viewportHeight - boundingBox.top - 100) + 'px';

  this.setupOverscroll_();

  // Update the tree.
  var rootSvg = this.rootSvg_;
  var tree = this.tree_;
  var vis = this.vis_;


  var ow = w + m[1] + m[3];
  var oh = h + m[0] + m[2];
  rootSvg
    .attr("width", ow)
    .attr("height", oh)
    .attr("style", "width: " + ow + "px; height: " + oh + "px");

  tree.size([w, h]);
  vis.attr("transform", "translate(" + m[3] + "," + m[0] + ")");

  return dimensions;
};


/**
 * Draws the tree.
 */
ImageHistoryTree.prototype.draw = function(container) {
  // Build the root of the tree.
  var result = this.buildRoot_();
  this.maxWidth_ = result['maxWidth'];
  this.maxHeight_ = result['maxHeight'];

  // Save the container.
  this.container_ = container;

  if (!$('#' + container)[0]) {
    this.container_ = null;
    return;
  }

  // Create the tree and all its components.
  var tree = d3.layout.tree()
    .separation(function() { return 2; });

  var diagonal = d3.svg.diagonal()
    .projection(function(d) { return [d.x, d.y]; });

  var rootSvg = d3.select("#" + container).append("svg:svg")
    .attr("class", "image-tree");

  var vis = rootSvg.append("svg:g");
  var formatComment = this.formatComment_;
  var formatTime = this.formatTime_;
  var formatCommand = this.formatCommand_;

  var tip = d3.tip()
    .attr('class', 'd3-tip')
    .offset([-1, 24])
    .direction('e')
    .html(function(d) {
      var html = '';
      if (d.virtual) {
        return d.name;
      }

      if (d.collapsed) {
        for (var i = 1; i < d.encountered.length; ++i) {
          html += '<span>' + d.encountered[i].image.id.substr(0, 12) + '</span>';
          html += '<span class="created">' + formatTime(d.encountered[i].image.created) + '</span>';
        }
        return html;
      }

      if (!d.image) {
        return '(This repository is empty)';
      }

      if (d.image.comment) {
        html += '<span class="comment">' + formatComment(d.image.comment) + '</span>';
      }
      if (d.image.command && d.image.command.length) {
        html += '<span class="command info-line"><i class="fa fa-terminal"></i>' + formatCommand(d.image) + '</span>';
      }
      html += '<span class="created info-line"><i class="fa fa-calendar"></i>' + formatTime(d.image.created) + '</span>';

      var tags = d.tags || [];
      html += '<span class="tooltip-tags tags">';
      for (var i = 0; i < tags.length; ++i) {
        var tag = tags[i];
        var kind = 'default';
        html += '<span class="label label-' + kind + ' tag" data-tag="' + tag + '">' + tag + '</span>';
      }
      html += '</span>';

      return html;
    })

  vis.call(tip);

  // Save all the state created.
  this.diagonal_ = diagonal;
  this.vis_ = vis;
  this.rootSvg_ = rootSvg;
  this.tip_ = tip;
  this.tree_ = tree;

  // Update the dimensions of the tree.
  var dimensions = this.updateDimensions_();
  if (!dimensions) {
    return this;
  }

  // Populate the tree.
  this.root_.x0 = dimensions.cw / 2;
  this.root_.y0 = 0;

  this.setTag_(this.currentTag_);
  this.setupOverscroll_();

  return this;
};


/**
 * Redraws the image history to fit the new size.
 */
ImageHistoryTree.prototype.notifyResized = function() {
  this.updateDimensions_();
  this.update_(this.root_);
};


/**
 * Sets the current tag displayed in the tree.
 */
ImageHistoryTree.prototype.setTag = function(tagName) {
  this.setTag_(tagName);
};


/**
 * Sets the current image displayed in the tree.
 */
ImageHistoryTree.prototype.setImage = function(imageId) {
  this.setImage_(imageId);
};


/**
 * Updates the highlighted path in the tree.
 */
ImageHistoryTree.prototype.setHighlightedPath_ = function(image) {
  if (this.currentNode_) {
    this.markPath_(this.currentNode_, false);
  }

  var imageByDockerId = this.imageByDockerId_;
  var currentNode = imageByDockerId[image.id];
  if (currentNode) {
    this.markPath_(currentNode, true);
    this.currentNode_ = currentNode;
  }
};


/**
 * Returns the ancestors of the given image.
 */
ImageHistoryTree.prototype.getAncestors_ = function(image) {
  var ancestorsString = image.ancestors;

  // Remove the starting and ending /s.
  ancestorsString = ancestorsString.substr(1, ancestorsString.length - 2);

  // Split based on /.
  ancestors = ancestorsString.split('/');
  return ancestors;
};


/**
 * Sets the current tag displayed in the tree and raises the event that the tag
 * was changed.
 */
ImageHistoryTree.prototype.changeTag_ = function(tagName) {
  $(this).trigger({
    'type': 'tagChanged',
    'tag': tagName
  });
  this.setTag_(tagName);
};


/**
 * Sets the current image displayed in the tree and raises the event that the image
 * was changed.
 */
ImageHistoryTree.prototype.changeImage_ = function(imageId) {
  $(this).trigger({
    'type': 'imageChanged',
    'image': this.findImage_(function(image) { return image.id == imageId; })
  });
  this.setImage_(imageId);
};


/**
 * Expands the given collapsed node in the tree.
 */
ImageHistoryTree.prototype.expandCollapsed_ = function(imageNode) {
  var index = imageNode.parent.children.indexOf(imageNode);
  if (index < 0 || imageNode.encountered.length < 2) {
    return;
  }

  // Note: we start at 1 since the 0th encountered node is the parent.
  imageNode.parent.children.splice(index, 1, imageNode.encountered[1]);
  this.maxHeight_ = this.determineMaximumHeight_(this.root_);
  this.update_(this.root_);
  this.updateDimensions_();
};


/**
 * Returns the level of the node in the tree. Recursively computes and updates
 * if necessary.
 */
ImageHistoryTree.prototype.calculateLevel_ = function(node) {
  if (node['level'] != null) {
    return node['level'];
  }

  if (node['parent'] == null) {
    return node['level'] = 0;
  }

  return node['level'] = (this.calculateLevel_(node['parent']) + 1);
};


/**
 * Builds the root node for the tree.
 */
ImageHistoryTree.prototype.buildRoot_ = function() {
  // Build the formatted JSON block for the tree. It must be of the form:
  //  {
  //    "name": "...",
  //    "children": [...]
  //  }
  var formatted = {"name": "No images found"};

  // Build a node for each image.
  var imageByDockerId = {};
  for (var i = 0; i < this.images_.length; ++i) {
    var image = this.images_[i];

    // Skip images that are currently uploading.
    if (image.uploading) { continue; }

    var imageNode = {
      "name": image.id.substr(0, 12),
      "children": [],
      "image": image,
      "tags": this.getTagsForImage_(image),
      "level": null
    };
    imageByDockerId[image.id] = imageNode;
  }
  this.imageByDockerId_ = imageByDockerId;

  // For each node, attach it to its immediate parent. If there is no immediate parent,
  // then the node is the root.
  var roots = [];
  var nodeCountsByLevel = {};
  for (var i = 0; i < this.images_.length; ++i) {
    var image = this.images_[i];

    // Skip images that are currently uploading.
    if (image.uploading) { continue; }

    var imageNode = imageByDockerId[image.id];
    var ancestors = this.getAncestors_(image);
    var immediateParent = ancestors[ancestors.length - 1];
    var parent = imageByDockerId[immediateParent];
    if (parent) {
      // Add a reference to the parent. This makes walking the tree later easier.
      imageNode.parent = parent;
      parent.children.push(imageNode);
    } else {
      imageNode['level'] = 0;
      roots.push(imageNode);
    }
  }

  // Calculate each node's level.
  for (var i = 0; i < this.images_.length; ++i) {
    var image = this.images_[i];

    // Skip images that are currently uploading.
    if (image.uploading) { continue; }

    var imageNode = imageByDockerId[image.id];
    var level = this.calculateLevel_(imageNode);
    if (nodeCountsByLevel[level] == null) {
      nodeCountsByLevel[level] = 1;
    } else {
      nodeCountsByLevel[level]++;
    }
  }

  // If there are multiple root nodes, then there is at least one branch without shared
  // ancestry and we use the virtual node. Otherwise, we use the root node found.
  var root = {
    'name': '',
    'children': roots,
    'virtual': true
  };

  if (roots.length == 1) {
    root = roots[0];
  }

  // Determine the maximum number of nodes at a particular level. This is used to size
  // the width of the tree properly.
  var maxChildCount = 0;
  var maxChildHeight = 0;
  Object.keys(nodeCountsByLevel).forEach(function(key){
    maxChildCount = Math.max(maxChildCount, nodeCountsByLevel[key]);
    maxChildHeight = Math.max(maxChildHeight, key);
  });

  // Recursively prune the nodes that are not referenced by a tag
  this.pruneUnreferenced_(root);

  // Compact the graph so that any single chain of three (or more) images becomes a collapsed
  // section. We only do this if the max width is > 1 (since for a single width tree, no long
  // chain will hide a branch).
  if (maxChildCount > 1) {
    this.collapseNodes_(root);
  }

  // Determine the maximum height of the tree, with collapsed nodes.
  var maxCollapsedHeight = this.determineMaximumHeight_(root);

  // Finally, set the root node and return.
  this.root_ = root;

  return {
    'maxWidth': maxChildCount + 1,
    'maxHeight': maxCollapsedHeight
  };
};


/**
 * Prunes images which are not referenced either directly or indirectly by any tag.
 */
ImageHistoryTree.prototype.pruneUnreferenced_ = function(node) {
  if (node.children) {
    var surviving_children = []
    for (var i = 0; i < node.children.length; ++i) {
      if (!this.pruneUnreferenced_(node.children[i])) {
        surviving_children.push(node.children[i]);
      }
    }
    node.children = surviving_children;
  }

  if (!node.tags) {
    return node.children.length == 0;
  }

  var tags = [];
  for (var i = 0; i < node.tags.length; ++i) {
    if (this.tagFilter_(node.tags[i])) {
      tags.push(node.tags[i]);
    }
  }

  return (node.children.length == 0 && tags.length == 0);
};


/**
 * Determines the height of the tree at its longest chain.
 */
ImageHistoryTree.prototype.determineMaximumHeight_ = function(node) {
  var maxHeight = 0;
  if (node.children) {
    for (var i = 0; i < node.children.length; ++i) {
      maxHeight = Math.max(this.determineMaximumHeight_(node.children[i]), maxHeight);
    }
  }
  return maxHeight + 1;
};


/**
 * Collapses long single chains of nodes (3 or more) into single nodes to make the graph more
 * compact.
 */
ImageHistoryTree.prototype.collapseNodes_ = function(node) {
  if (node.children && node.children.length == 1) {
    // Keep searching downward until we find a node with more than a single child.
    var current = node;
    var previous = node;
    var encountered = [];
    while (current.children
          && current.children.length == 1
           && current.tags
           && current.tags.length == 0) {
      encountered.push(current);
      previous = current;
      current = current.children[0];
    }

    if (encountered.length >= 3) {
      // Collapse the node.
      var collapsed = {
        "name": '(' + (encountered.length - 1) + ' images)',
        "children": [current],
        "collapsed": true,
        "encountered": encountered
      };
      node.children = [collapsed];

      // Update the parent relationships.
      collapsed.parent = node;
      current.parent = collapsed;
      return;
    }
  }

  if (node.children) {
    for (var i = 0; i < node.children.length; ++i) {
      this.collapseNodes_(node.children[i]);
    }
  }
};


/**
 * Determines the maximum child count for the node and its children.
 */
ImageHistoryTree.prototype.determineMaximumChildCount_ = function(node) {
  var children = node.children;
  var myLevelCount = children.length;
  var nestedCount = 0;

  for (var i = 0; i < children.length; ++i) {
    nestedCount += children[i].children.length;
  }

  return Math.max(myLevelCount, nestedCount);
};


/**
 * Finds the image where the checker function returns true and returns it or null
 * if none.
 */
ImageHistoryTree.prototype.findImage_ = function(checker) {
  for (var i = 0; i < this.images_.length; ++i) {
    var image = this.images_[i];
    if (checker(image)) {
      return image;
    }
  }

  return null;
};


/**
 * Marks the full node path from the given starting node on whether it is highlighted.
 */
ImageHistoryTree.prototype.markPath_ = function(startingNode, isHighlighted) {
  var currentNode = startingNode;
  currentNode.current = isHighlighted;
  while (currentNode != null) {
    currentNode.highlighted = isHighlighted;
    currentNode = currentNode.parent;
  }
};


/**
 * Sets the current tag displayed in the tree.
 */
ImageHistoryTree.prototype.setTag_ = function(tagName) {
  if (tagName == this.currentTag_) {
    return;
  }

  var imageByDockerId = this.imageByDockerId_;

  // Save the current tag.
  var previousTagName = this.currentTag_;
  this.currentTag_ = tagName;
  this.currentImage_ = null;

  // Update the path.
  var that = this;
  var tagImage = this.findImage_(function(image) {
    return tagName && (that.getTagsForImage_(image).indexOf(tagName) >= 0);
  });

  if (tagImage) {
    this.setHighlightedPath_(tagImage);
  }

  // Ensure that the children are in the correct order.
  for (var i = 0; i < this.images_.length; ++i) {
    var image = this.images_[i];

    // Skip images that are currently uploading.
    if (image.uploading) { continue; }

    var imageNode = this.imageByDockerId_[image.id];
    var ancestors = this.getAncestors_(image);
    var immediateParent = ancestors[ancestors.length - 1];
    var parent = imageByDockerId[immediateParent];
    if (parent && imageNode.highlighted) {
      var arr = parent.children;
      if (parent._children) {
        arr = parent._children;
      }

      if (arr[0] != imageNode) {
        var index = arr.indexOf(imageNode);
        if (index > 0) {
          arr.splice(index, 1);
          arr.splice(0, 0, imageNode);
        }
      }
    }
  }

  // Update the tree.
  this.update_(this.root_);
};


/**
 * Sets the current image highlighted in the tree.
 */
ImageHistoryTree.prototype.setImage_ = function(imageId) {
  // Find the new current image.
  var newImage = this.findImage_(function(image) {
    return image.id == imageId;
  });

  if (newImage == this.currentImage_) {
    return;
  }

  this.setHighlightedPath_(newImage);
  this.currentImage_ = newImage;
  this.currentTag_ = null;
  this.update_(this.root_);
};


/**
 * Updates the tree in response to a click on a node.
 */
ImageHistoryTree.prototype.update_ = function(source) {
  var tree = this.tree_;
  var vis = this.vis_;
  var diagonal = this.diagonal_;
  var tip = this.tip_;
  var currentTag = this.currentTag_;
  var currentImage = this.currentImage_;
  var repoNamespace = this.repoNamespace_;
  var repoName = this.repoName_;
  var maxHeight = this.maxHeight_;

  var that = this;

  var duration = 500;

  // Compute the new tree layout.
  var nodes = tree.nodes(this.root_).reverse();

  // Normalize for fixed-depth.
  nodes.forEach(function(d) { d.y = (maxHeight - d.depth - 1) * DEPTH_HEIGHT; });

  // Update the nodes...
  var node = vis.selectAll("g.node")
    .data(nodes, function(d) { return d.id || (d.id = that.idCounter_++); });

  // Enter any new nodes at the parent's previous position.
  var nodeEnter = node.enter().append("svg:g")
    .attr("class", "node")
    .attr("transform", function(d) { return "translate(" + source.x0 + "," + source.y0 + ")"; });

  nodeEnter.append("svg:circle")
    .attr("r", 1e-6)
    .style("fill", function(d) { return d._children ? "lightsteelblue" : "#fff"; })
    .on("click", function(d) { that.toggle_(d); that.update_(d); });

  // Create the group that will contain the node name and its tags.
  var g = nodeEnter.append("svg:g").style("fill-opacity", 1e-6);

  // Add the repo ID.
  g.append("svg:text")
    .attr("x", function(d) { return d.children || d._children ? -10 : 10; })
    .attr("dy", ".35em")
    .attr("text-anchor", function(d) { return d.children || d._children ? "end" : "start"; })
    .text(function(d) { return d.name; })
    .on("click", function(d) {
      if (d.image) { that.changeImage_(d.image.id); }
      if (d.collapsed) { that.expandCollapsed_(d); }
    })
    .on('mouseover', tip.show)
    .on('mouseout', tip.hide)
    .on("contextmenu", function(d, e) {
      d3.event.preventDefault();

      if (d.image) {
        $(that).trigger({
          'type': 'showImageMenu',
          'image': d.image.id,
          'clientX': d3.event.clientX,
          'clientY': d3.event.clientY
        });
      }
    });

  nodeEnter.selectAll("tags")
    .append("svg:text")
    .text("bar");

  // Create the foreign object to hold the tags (if any).
  var fo = g.append("svg:foreignObject")
    .attr("class", "fo")
    .attr("x", 14)
    .attr("y", 12)
    .attr("width", 110)
    .attr("height", DEPTH_HEIGHT - 20);

  // Add the tags container.
  fo.append('xhtml:div')
    .attr("class", "tags")
    .style("display", "none");

  // Translate the foreign object so the tags are under the ID.
  fo.attr("transform", function(d, i) {
    return "translate(" + [-130, 0 ] + ")";
  });

  // Transition nodes to their new position.
  var nodeUpdate = node.transition()
    .duration(duration)
    .attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });

  // Update the node circle.
  nodeUpdate.select("circle")
    .attr("r", 4.5)
    .attr("class", function(d) {
      return (d._children ? "closed " : "open ") + (d.current ? "current " : "") + (d.highlighted ? "highlighted " : "");
    })
    .style("fill", function(d) {
      if (d.current) {
        return "";
      }
      return d._children ? "lightsteelblue" : "#fff";
    });

  // Update the repo text.
  nodeUpdate.select("text")
    .attr("class", function(d) {
      if (d.collapsed) {
        return 'collapsed';
      }
      if (d.virtual) {
        return 'virtual';
      }
      if (!currentImage) {
	return '';
      }
      return d.image.id == currentImage.id ? 'current' : '';
    });

  // Ensure that the node is visible.
  nodeUpdate.select("g")
    .style("fill-opacity", 1);

  // Update the tags.
  node.select(".tags")
    .html(function(d) {
      if (!d.tags) {
        return '';
      }

      var html = '<div style="width: ' + DEPTH_HEIGHT + 'px">';
      for (var i = 0; i < d.tags.length; ++i) {
        var tag = d.tags[i];
        var kind = 'default';
        if (tag == currentTag) {
          kind = 'success';
        }
        html += '<span class="label label-' + kind + ' tag" data-tag="' + tag + '" title="' + tag + '" style="max-width: ' + DEPTH_HEIGHT + 'px">' + tag + '</span>';
      }
      html += '</div>';
      return html;
    });

  // Listen for click events on the labels.
  node.selectAll(".tag")
    .on("click", function(d, e) {
      var tag = this.getAttribute('data-tag');
      if (tag) {
        that.changeTag_(tag);
      }
    })
    .on("contextmenu", function(d, e) {
      d3.event.preventDefault();

      var tag = this.getAttribute('data-tag');
      if (tag) {
        $(that).trigger({
          'type': 'showTagMenu',
          'tag': tag,
          'clientX': d3.event.clientX,
          'clientY': d3.event.clientY
        });
      }
    });

  // Ensure the tags are visible.
  nodeUpdate.select(".tags")
    .style("display", "")

  // There is a bug in Chrome which sometimes prevents the foreignObject from redrawing. To that end,
  // we force a redraw by adjusting the height of the object ever so slightly.
  nodeUpdate.select(".fo")
    .attr('height', function(d) {
      return DEPTH_HEIGHT - 20 + Math.random() / 10;
    });

  // Transition exiting nodes to the parent's new position.
  var nodeExit = node.exit().transition()
    .duration(duration)
    .attr("transform", function(d) { return "translate(" + source.x + "," + source.y + ")"; })
    .remove();

  nodeExit.select("circle")
    .attr("r", 1e-6);

  nodeExit.select(".tags")
    .style("display", "none");

  nodeExit.select("g")
    .style("fill-opacity", 1e-6);

  // Update the links...
  var link = vis.selectAll("path.link")
    .data(tree.links(nodes), function(d) { return d.target.id; });

  // Enter any new links at the parent's previous position.
  link.enter().insert("svg:path", "g")
    .attr("class", function(d) {
      var isHighlighted = d.target.highlighted;
      return "link " + (isHighlighted ? "highlighted": "");
    })
    .attr("d", function(d) {
      var o = {x: source.x0, y: source.y0};
      return diagonal({source: o, target: o});
    })
    .transition()
    .duration(duration)
    .attr("d", diagonal);

  // Transition links to their new position.
  link.transition()
    .duration(duration)
    .attr("d", diagonal)
    .attr("class", function(d) {
      var isHighlighted = d.target.highlighted;
      return "link " + (isHighlighted ? "highlighted": "");
    });

  // Transition exiting nodes to the parent's new position.
  link.exit().transition()
    .duration(duration)
    .attr("d", function(d) {
      var o = {x: source.x, y: source.y};
      return diagonal({source: o, target: o});
    })
    .remove();

  // Stash the old positions for transition.
  nodes.forEach(function(d) {
    d.x0 = d.x;
    d.y0 = d.y;
  });
};


/**
 * Toggles children of a node.
 */
ImageHistoryTree.prototype.toggle_ = function(d) {
  if (d.children) {
    d._children = d.children;
    d.children = null;
  } else {
    d.children = d._children;
    d._children = null;
  }
};


/**
 * Disposes of the tree.
 */
ImageHistoryTree.prototype.dispose = function() {
  var container =  this.container_ ;
  $('#' + container).removeOverscroll();
  $('#' + container).html('');
};

////////////////////////////////////////////////////////////////////////////////

/**
 * Based off of http://bl.ocks.org/mbostock/1346410
 */
export function UsageChart() {
  this.total_ = null;
  this.count_ = null;
  this.drawn_ = false;
}


/**
 * Updates the chart with the given count and total of number of repositories.
 */
UsageChart.prototype.update = function(count, total) {
  if (!this.g_) { return; }
  this.total_ = total;
  this.count_ = count;
  this.drawInternal_();
};


/**
 * Conducts the actual draw or update (if applicable).
 */
UsageChart.prototype.drawInternal_ = function() {
  // If the total is null, then we have not yet set the proper counts.
  if (this.total_ === null) { return; }

  var duration = 750;

  var arc = this.arc_;
  var pie = this.pie_;
  var arcTween = this.arcTween_;

  var color = d3.scale.category20();
  var count = this.count_;
  var total = this.total_;

  var data = [Math.max(count, 1), Math.max(0, total - count)];

  var arcTween = function(a) {
    var i = d3.interpolate(this._current, a);
    this._current = i(0);
    return function(t) {
      return arc(i(t));
    };
  };

  if (!this.drawn_) {
    var text = this.g_.append("svg:text")
      .attr("dy", 10)
      .attr("dx", 0)
      .attr('dominant-baseline', 'auto')
      .attr('text-anchor', 'middle')
      .attr('class', 'count-text')
      .text(this.count_ + ' / ' + this.total_);

    var path = this.g_.datum(data).selectAll("path")
      .data(pie)
      .enter().append("path")
      .attr("fill", function(d, i) { return color(i); })
      .attr("class", function(d, i) { return 'arc-' + i; })
      .attr("d", arc)
      .each(function(d) { this._current = d; }); // store the initial angles

    this.path_ = path;
    this.text_ = text;
  } else {
    pie.value(function(d, i) { return data[i]; }); // change the value function
    this.path_ = this.path_.data(pie); // compute the new angles
    this.path_.transition().duration(duration).attrTween("d", arcTween); // redraw the arcs

    // Update the text.
    this.text_.text(this.count_ + ' / ' + this.total_);
  }

  this.drawn_ = true;
};


/**
 * Draws the chart in the given container.
 */
UsageChart.prototype.draw = function(container) {
  var cw = 200;
  var ch = 200;
  var radius = Math.min(cw, ch) / 2;

  var pie = d3.layout.pie().sort(null);

  var arc = d3.svg.arc()
    .innerRadius(radius - 50)
    .outerRadius(radius - 25);

  var svg = d3.select("#" + container).append("svg:svg")
    .attr("width", cw)
    .attr("height", ch);

  var g = svg.append("g")
    .attr("transform", "translate(" + cw / 2 + "," + ch / 2 + ")");

  this.svg_ = svg;
  this.g_ = g;
  this.pie_ = pie;
  this.arc_ = arc;
  this.width_ = cw;
  this.drawInternal_();
};


////////////////////////////////////////////////////////////////////////////////

/**
 * A chart which displays the last seven days of actions in the account.
 */
export function LogUsageChart(titleMap) {
  this.titleMap_ = titleMap;
  this.colorScale_ = d3.scale.category20();
  this.entryMap_ = {};
}

/**
 * Builds the D3-representation of the data.
 */
LogUsageChart.prototype.buildData_ = function(aggregatedLogs) {
  var parseDate = d3.time.format("%a, %d %b %Y %H:%M:%S %Z").parse

  // Build entries for each kind of event that occurred, on each day. We have one
  // entry per {kind, day} pair.
  var entries = [];
  for (var i = 0; i < aggregatedLogs.length; ++i) {
    var aggregated = aggregatedLogs[i];
    var title = this.titleMap_[aggregated.kind] || aggregated.kind;
    var datetime = parseDate(aggregated.datetime);

    var day = ('0' + datetime.getDate()).slice(-2);
    var month = ('0' + (datetime.getMonth() + 1)).slice(-2);

    var formatted = month + '/' + day;
    var justdate = new Date(datetime.getFullYear(), datetime.getMonth(), datetime.getDate());
    var key = title + '_' + formatted;
    var entry = {
      'kind': aggregated.kind,
      'title': title,
      'justdate': justdate,
      'formatted': datetime.getDate(),
      'count': aggregated.count
    };

    entries.push(entry);
    this.entryMap_[key] = entry;
  }

  // Build the data itself. We create a single entry for each possible kind of data, and then add (x, y) pairs
  // for the number of times that kind of event occurred on a particular day.
  var dataArray = [];
  var dataMap = {};
  var dateMap = {};

  for (var i = 0; i < entries.length; ++i) {
    var entry = entries[i];
    var key = entry.title;
    var found = dataMap[key];
    if (!found) {
      found = {'key': key, 'values': [], 'kind': entry.kind};
      dataMap[key] = found;
      dataArray.push(found);
    }

    found.values.push({
      'x': entry.justdate,
      'y': entry.count
    });

    dateMap[entry.justdate.toString()] = entry.justdate;
  }

  // Note: nvd3 has a bug that causes d3 to fail if there is not an entry for every single
  // kind on each day that has data. Therefore, we pad those days with 0-length entries for each
  // kind.
  for (var i = 0; i < dataArray.length; ++i) {
    var datum = dataArray[i];
    for (var sDate in dateMap) {
      if (!dateMap.hasOwnProperty(sDate)) {
        continue;
      }

      var cDate = dateMap[sDate];
      var found = false;
      for (var j = 0; j < datum.values.length; ++j) {
        if (datum.values[j]['x'].getDate() == cDate.getDate()) {
          found = true;
          break;
        }
      }

      if (!found) {
        datum.values.push({
          'x': cDate,
          'y': 0
        });
      }
    }

    datum.values.sort(function(a, b) {
      return (a['x'].getDate() * 1) - (b['x'].getDate() * 1);
    });
  }

  return this.data_ = dataArray;
};


/**
 * Renders the tooltip when hovering over an element in the chart.
 */
LogUsageChart.prototype.renderTooltip_ = function(d, e) {
  var key = d + '_' + e;
  var entry = this.entryMap_[key];
  if (!entry) {
    entry = {'count': 0};
  }

  var s = entry.count == 1 ? '' : 's';
  return d + ' - ' + entry.count + ' time' + s + ' on ' + e;
};


/**
 * Returns the color used in the chart for log entries of the given
 * kind.
 */
LogUsageChart.prototype.getColor = function(kind) {
  var colors = this.colorScale_.range();
  var index = 0;
  for (var i = 0; i < this.data_.length; ++i) {
    var datum = this.data_[i];
    var key = this.titleMap_[kind] || kind;
    if (datum.key == key) {
      index = i;
      break;
    }
  }

  return colors[index];
};


/**
 * Handler for when an element in the chart has been clicked.
 */
LogUsageChart.prototype.handleElementClicked_ = function(e) {
  var key = e.series.key;
  var kind = e.series.kind;
  var disabled = [];

  var enabledCount = 0;
  var d = this.chart_.multibar.disabled();
  for (var i = 0; i < this.data_.length; ++i) {
    enabledCount += (d[i] ? 0 : 1);
  }

  for (var i = 0; i < this.data_.length; ++i) {
    disabled.push(enabledCount == 1 ? false : this.data_[i].key != key);
  }

  var allowed = {};
  allowed[kind] = true;

  this.chart_.dispatch.changeState({ 'disabled': disabled });
  $(this).trigger({
    'type': 'filteringChanged',
    'allowed': enabledCount == 1 ? null : allowed
  });
};


/**
 * Handler for when the state of the chart has changed.
 */
LogUsageChart.prototype.handleStateChange_ = function(e) {
  var allowed = {};
  var disabled = e.disabled;
  for (var i = 0; i < this.data_.length; ++i) {
    if (!disabled[i]) {
      allowed[this.data_[i].kind] = true;
    }
  }

  $(this).trigger({
    'type': 'filteringChanged',
    'allowed': allowed
  });
};


/**
 * Draws the chart in the given container element.
 */
LogUsageChart.prototype.draw = function(container, logData, startDate, endDate) {
  // Reset the container's contents.
  var containerElm = document.getElementById(container);
  if (!containerElm) {
    return;
  }

  containerElm.innerHTML = '<svg></svg>';

  // Returns a date offset from the given date by "days" Days.
  var offsetDate = function(d, days) {
    var copy = new Date(d.getTime());
    copy.setDate(copy.getDate() + days);
    return copy;
  };

  var that = this;
  var data = this.buildData_(logData);
  nv.addGraph(function() {
    // Build the chart itself.
    var chart = nv.models.multiBarChart()
      .margin({top: 30, right: 30, bottom: 50, left: 60})
      .stacked(false)
      .staggerLabels(false)
      .tooltip(function(d, e) {
        return that.renderTooltip_(d, e);
      })
      .color(that.colorScale_.range())
      .groupSpacing(0.1);

    chart.multibar.delay(0);

    // Create the x-axis domain to encompass the full date range.
    var domain = [];
    var datetime = startDate;
    while (datetime <= endDate) {
      domain.push(datetime);
      datetime = offsetDate(datetime, 1);
    }

    chart.xDomain(domain);

    // Finish setting up the chart.
    chart.xAxis
      .tickFormat(d3.time.format("%m/%d"));

    chart.yAxis
      .tickFormat(d3.format(',f'));

    d3.select('#bar-chart svg')
      .datum(data)
      .transition()
      .duration(500)
      .call(chart);

    nv.utils.windowResize(chart.update);

    chart.multibar.dispatch.on('elementClick', function(e) { that.handleElementClicked_(e); });
    chart.dispatch.on('stateChange', function(e) { that.handleStateChange_(e); });
    return that.chart_ = chart;
  });
};
