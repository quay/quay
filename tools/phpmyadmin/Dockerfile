FROM phusion/baseimage:0.9.9

ENV DEBIAN_FRONTEND noninteractive
ENV HOME /root
ENV UPDATE_APT 2

RUN apt-get update

# Install LAMP
RUN apt-get install -y lamp-server^

# Install phpMyAdmin
RUN mysqld & \
	service apache2 start; \
	sleep 5; \
	printf y\\n\\n\\n1\\n | apt-get install -y phpmyadmin; \
	sleep 15; \
	mysqladmin -u root shutdown


# Setup phpmyadmin to run
RUN echo "Include /etc/phpmyadmin/apache.conf" >> /etc/apache2/apache2.conf
RUN rm /etc/phpmyadmin/config.inc.php

ADD config.inc.php /etc/phpmyadmin/config.inc.php

ADD run-admin.sh /etc/service/phpadmin/run

EXPOSE 80

CMD ["/sbin/my_init"]