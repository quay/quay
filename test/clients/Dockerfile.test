FROM quay.io/quay/busybox
RUN date > somefile
RUN date +%s%N > anotherfile
RUN date +"%T.%N" > thirdfile
RUN echo "testing 123" > testfile
