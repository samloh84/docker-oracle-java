FROM samloh84/centos:7

ARG VENDOR=oracle
ARG PRODUCT=server-jre
ARG PRODUCT_VERSION=8u152-b16
ARG TEMP_DIR_ROOT=/tmp/${VENDOR}-${PRODUCT}
ARG TEMP_DIR=/${TEMP_DIR_ROOT}/${PRODUCT_VERSION}
ARG INSTALL_DIR_ROOT=/usr/java
ARG INSTALL_DIR=${INSTALL_DIR_ROOT}/server-jre1.8.0_152
ARG ORACLE_USERNAME
ARG ORACLE_PASSWORD
ARG SERVER_JRE_INSTALL_TAR_GZ_URL=http://download.oracle.com/otn-pub/java/jdk/8u152-b16/aa0333dd3019491ca4f6ddbe78cdb6d0/server-jre-8u152-linux-x64.tar.gz
ARG SERVER_JRE_INSTALL_TAR_GZ=server-jre-8u152-linux-x64.tar.gz

ARG JCE_POLICY_ZIP_URL=http://download.oracle.com/otn-pub/java/jce/8/jce_policy-8.zip
ARG JCE_POLICY_ZIP=jce_policy-8.zip

USER ${ROOT_UID}

COPY downloader.py java-import-ca-cert ${TEMP_DIR}/

RUN \
yum-install unzip python-requests && \
mkdir -p ${TEMP_DIR} && \
pushd ${TEMP_DIR} && \
cp java-import-ca-cert /usr/local/bin/ && \
chmod a+xs /usr/local/bin/java-import-ca-cert && \
python2 downloader.py \
--url ${SERVER_JRE_INSTALL_TAR_GZ_URL} \
--filename ${SERVER_JRE_INSTALL_TAR_GZ} \
--username ${ORACLE_USERNAME} \
--password ${ORACLE_PASSWORD} && \
mkdir -p ${INSTALL_DIR} && \
tar -xzf ${SERVER_JRE_INSTALL_TAR_GZ} --strip-components=1 -C ${INSTALL_DIR} && \
python2 downloader.py \
--url ${JCE_POLICY_ZIP_URL} \
--filename ${JCE_POLICY_ZIP} \
--username ${ORACLE_USERNAME} \
--password ${ORACLE_PASSWORD} && \
unzip -qq ${JCE_POLICY_ZIP} -d ${TEMP_DIR}/jce && \
find ${TEMP_DIR}/jce -name "*.jar" -print0 | xargs -0 mv -t ${INSTALL_DIR}/jre/lib/security && \
popd && \
rm -rf ${TEMP_DIR_ROOT} && \
yum-install remove python-requests


ENV JAVA_HOME ${INSTALL_DIR}
ENV PATH ${JAVA_HOME}/bin:${JAVA_HOME}/jre/bin:${PATH}

USER ${APP_UID}