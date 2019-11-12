<?php
/**
 * Debian local configuration file
 *
 * This file overrides the settings made by phpMyAdmin interactive setup
 * utility.
 *
 * For example configuration see
 *   /usr/share/doc/phpmyadmin/examples/config.sample.inc.php
 * or
 *   /usr/share/doc/phpmyadmin/examples/config.manyhosts.inc.php
 *
 * NOTE: do not add security sensitive data to this file (like passwords)
 * unless you really know what you're doing. If you do, any user that can
 * run PHP or CGI on your webserver will be able to read them. If you still
 * want to do this, make sure to properly secure the access to this file
 * (also on the filesystem level).
 */

// Load secret generated on postinst
include('/var/lib/phpmyadmin/blowfish_secret.inc.php');

// Load autoconf local config
include('/var/lib/phpmyadmin/config.inc.php');

/**
 * Server(s) configuration
 */
$i = 0;
// The $cfg['Servers'] array starts with $cfg['Servers'][1].  Do not use $cfg['Servers'][0].
// You can disable a server config entry by setting host to ''.
$i++;

/**
 * Read configuration from dbconfig-common
 * You can regenerate it using: dpkg-reconfigure -plow phpmyadmin
 */
if (is_readable('/etc/phpmyadmin/config-db.php')) {
    require('/etc/phpmyadmin/config-db.php');
} else {
    error_log('phpmyadmin: Failed to load /etc/phpmyadmin/config-db.php.'
        . ' Check group www-data has read access.');
}

$cfg['Servers'][$i]['auth_type'] = 'HTTP';
$cfg['Servers'][$i]['hide_db'] = '(mysql|information_schema|phpmyadmin)';
/* Server parameters */
$cfg['Servers'][$i]['host'] = 'db1.quay.io';
$cfg['Servers'][$i]['ssl'] = true;

/*
 * End of servers configuration
 */

/*
 * Directories for saving/loading files from server
 */
$cfg['UploadDir'] = '';
$cfg['SaveDir'] = '';
