FROM samloh84/centos:7

ARG VENDOR=oracle
ARG PRODUCT=jdk
ARG PRODUCT_VERSION=7u80-b15
ARG TEMP_DIR_ROOT=/tmp/${VENDOR}-${PRODUCT}
ARG TEMP_DIR=/${TEMP_DIR_ROOT}/${PRODUCT_VERSION}
ARG INSTALL_DIR_ROOT=/usr/java
ARG INSTALL_DIR=${INSTALL_DIR_ROOT}/jdk1.7.0_80
ARG ORACLE_USERNAME
ARG ORACLE_PASSWORD
ARG JDK_INSTALL_RPM_URL=http://download.oracle.com/otn/java/jdk/7u80-b15/jdk-7u80-linux-x64.rpm
ARG JDK_INSTALL_RPM=jdk-7u80-linux-x64.rpm

ARG JCE_POLICY_ZIP_URL=http://download.oracle.com/otn-pub/java/jce/7/UnlimitedJCEPolicyJDK7.zip
ARG JCE_POLICY_ZIP=UnlimitedJCEPolicyJDK7.zip

USER ${ROOT_UID}

COPY downloader.py java-import-ca-cert ${TEMP_DIR}/

RUN \
yum-install unzip python-requests && \
mkdir -p ${TEMP_DIR} && \
pushd ${TEMP_DIR} && \
cp java-import-ca-cert /usr/local/bin/ && \
chmod a+xs /usr/local/bin/java-import-ca-cert && \
python2 downloader.py \
--url ${JDK_INSTALL_RPM_URL} \
--filename ${JDK_INSTALL_RPM} \
--username ${ORACLE_USERNAME} \
--password ${ORACLE_PASSWORD} && \
yum-install ${TEMP_DIR}/${JDK_INSTALL_RPM} && \

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