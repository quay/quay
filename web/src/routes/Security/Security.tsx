import React from 'react';
import {
  PageSection,
  PageSectionVariants,
  Text,
  TextContent,
  TextVariants,
} from '@patternfly/react-core';
import './css/Security.scss';

export const Security: React.FC = () => {
  return (
    <>
      <PageSection variant={PageSectionVariants.light}>
        <TextContent>
          <Text component={TextVariants.h1}>Quay Security</Text>
        </TextContent>
      </PageSection>
      <PageSection
        variant={PageSectionVariants.default}
        className="security-page"
      >
        <TextContent>
          <Text component={TextVariants.p}>
            We understand that when you upload one of your repositories to Quay
            that you are trusting us with some potentially very sensitive data.
            On this page we will lay out our security features and practices to
            help you make an informed decision about whether you can trust us
            with your data.
          </Text>

          <Text component={TextVariants.h2} style={{marginTop: '2rem'}}>
            SSL Everywhere
          </Text>
          <Text component={TextVariants.p}>
            We expressly forbid connections to Quay using unencrypted HTTP
            traffic. This helps keep your data and account information safe on
            the wire. Our SSL traffic is decrypted on our application servers,
            so your traffic is encrypted even within the datacenter. We use a
            4096-bit RSA key, and after the key exchange is complete, traffic is
            transferred using 256-bit AES, for the maximum encryption strength.
          </Text>

          <Text component={TextVariants.h2} style={{marginTop: '2rem'}}>
            Encryption
          </Text>
          <Text component={TextVariants.p}>
            Our binary data is currently stored in Amazon&apos;s{' '}
            <a
              href="https://aws.amazon.com/s3/"
              target="_blank"
              rel="noopener noreferrer"
            >
              S3
            </a>{' '}
            service. We use HTTPS when transferring your data internally between
            our application servers and S3, so your data is never exposed in
            plain text on the internet. We use their{' '}
            <a
              href="https://docs.aws.amazon.com/AmazonS3/latest/dev/UsingServerSideEncryption.html"
              target="_blank"
              rel="noopener noreferrer"
            >
              server side encryption
            </a>{' '}
            to protect your data while stored at rest in their data centers.
          </Text>

          <Text component={TextVariants.h2} style={{marginTop: '2rem'}}>
            Passwords
          </Text>
          <Text component={TextVariants.p}>
            There have been a number of high profile leaks recently where
            companies have been storing their customers&apos; passwords in plain
            text, an unsalted hash, or a{' '}
            <a
              href="https://en.wikipedia.org/wiki/Salt_(cryptography)"
              target="_blank"
              rel="noopener noreferrer"
            >
              salted hash
            </a>{' '}
            where every salt is the same. At Quay we use the{' '}
            <a
              href="https://en.wikipedia.org/wiki/Bcrypt"
              target="_blank"
              rel="noopener noreferrer"
            >
              bcrypt
            </a>{' '}
            algorithm to generate a salted hash from your password, using a
            unique salt for each password. This method of storage is safe
            against{' '}
            <a
              href="https://en.wikipedia.org/wiki/Rainbow_table"
              target="_blank"
              rel="noopener noreferrer"
            >
              rainbow attacks
            </a>{' '}
            and is obviously superior to plain-text storage. Your credentials
            are also never written in plain text to our application logs, a leak
            that is commonly overlooked.
          </Text>

          <Text component={TextVariants.h2} style={{marginTop: '2rem'}}>
            Access Controls
          </Text>
          <Text component={TextVariants.p}>
            Repositories will only ever be shared with people to whom you
            delegate access. Repositories created from the Docker command line
            are private by default and must be made public with an explicit
            action in the Quay UI. We have a test suite which is run before
            every code push which tests all methods which expose private data
            with all levels of access to ensure nothing is accidentally leaked.
          </Text>

          <Text component={TextVariants.h2} style={{marginTop: '2rem'}}>
            Firewalls
          </Text>
          <Text component={TextVariants.p}>
            Our application servers and database servers are all protected with
            firewall settings that only allow communication with known hosts and
            host groups on sensitive ports (e.g. SSH). None of our servers have
            SSH password authentication enabled, preventing brute force password
            attacks.
          </Text>

          <Text component={TextVariants.h2} style={{marginTop: '2rem'}}>
            Data Resilience
          </Text>
          <Text component={TextVariants.p}>
            While not related directly to security, many of you are probably
            worried about whether you can depend on the data you store in Quay.
            All binary data that we store is stored in Amazon S3 at the highest
            redundancy level, which Amazon claims provides{' '}
            <a
              href="https://aws.amazon.com/s3/faqs/#How_is_Amazon_S3_designed_to_achieve_99.999999999%_durability"
              target="_blank"
              rel="noopener noreferrer"
            >
              11-nines of durability
            </a>
            . Our service metadata (e.g. logins, tags, teams) is stored in a
            database which is backed up nightly, and backups are preserved for 7
            days.
          </Text>
        </TextContent>
      </PageSection>
    </>
  );
};

export default Security;
