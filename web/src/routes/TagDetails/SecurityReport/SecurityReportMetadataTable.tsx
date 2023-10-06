import React from 'react';
import {Text, TextContent, TextVariants} from '@patternfly/react-core';
import {Table, Tbody, Th, Thead, Tr} from '@patternfly/react-table';
import {ExclamationTriangleIcon} from '@patternfly/react-icons';
import {MinusCircleIcon} from '@patternfly/react-icons';
import {VulnerabilityListItem} from './Types';

const getDistro = function (vuln: VulnerabilityListItem) {
  if (vuln.Metadata.DistroName) {
    return vuln.NamespaceName.split(':', 1);
  }
  return 'Unknown';
};

const getSeverityTooltip = function (vuln: VulnerabilityListItem) {
  const distro = getDistro(vuln);

  let result =
    'Note: This vulnerability was originally given a CVSSv3 score of ' +
    vuln.Metadata.NVD.CVSSv3.Score +
    ' by NVD';

  if (vuln.Severity != 'Unknown') {
    result =
      result + ', but was subsequently reclassified as a ' + vuln.Severity;
  }

  if (distro != 'Unknown') {
    result = result + ' issued by ' + distro;
  }
  return result;
};

const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case 'high':
      return <ExclamationTriangleIcon color={'#C9190B'} />;
    case 'medium':
      return <ExclamationTriangleIcon color={'#EC7A08'} />;
    case 'low':
      return <MinusCircleIcon color={'#3E8635'} />;
  }
};

export function SecurityReportMetadataTable(
  props: SecurityDetailsMetadataProps,
) {
  return (
    <TextContent style={{paddingRight: '30px'}}>
      <Text component={TextVariants.p}>Severity Note</Text>
      <Text component={TextVariants.small}>
        {getSeverityTooltip(props.vulnerability)}
      </Text>

      <Text component={TextVariants.p}>Vectors</Text>
      <Table aria-label="Vulnerabilities" variant="compact">
        <Thead cellPadding={'5px'}>
          <Tr marginWidth={0} className="pf-v5-u-text-align-left">
            {props.vulnerability.Metadata.NVD.CVSSv3.Vectors.split('/')
              .slice(1)
              .map((vector, i) => {
                return (
                  <Th key={i} modifier="nowrap">
                    {NVD_VECTORS[vector.split(':')[0]]?.title}
                  </Th>
                );
              })}
          </Tr>
        </Thead>
        <Tbody>
          <Tr>
            {props.vulnerability.Metadata.NVD.CVSSv3.Vectors.split('/')
              .slice(1)
              .map((vector, i) => {
                const vectorType = vector.split(':')[0];
                const vectorValue = vector.split(':')[1];
                const title = NVD_VECTORS[vectorType].values.filter(
                  (value) => value.id == vectorValue,
                )[0].title;
                const severity = NVD_VECTORS[vectorType].values.filter(
                  (value) => value.id == vectorValue,
                )[0].severity;
                return (
                  <Th key={i} modifier="nowrap">
                    {getSeverityIcon(severity)} {title}
                  </Th>
                );
              })}
          </Tr>
        </Tbody>
      </Table>
      {props.vulnerability.Description && (
        <>
          <Text component={TextVariants.p}>Description</Text>
          <Text component={TextVariants.small}>
            {props.vulnerability.Description}
          </Text>
        </>
      )}
    </TextContent>
  );
}

const NVD_VECTORS = {
  AV: {
    title: 'Attack Vector',
    description:
      'This metric reflects how the vulnerability is exploited. The more remote an attacker can be to attack a host, the greater the vulnerability score.',
    values: [
      {
        id: 'N',
        title: 'Network',
        description:
          'A vulnerability exploitable with network access means the vulnerable software is bound to the network stack and the attacker does not require local network access or local access.  Such a vulnerability is often termed "remotely exploitable". For example, an attacker causing a denial of service (DoS) by sending a specially crafted TCP packet across a wide area network.',
        severity: 'high',
      },
      {
        id: 'A',
        title: 'Adjacent Network',
        description:
          'A vulnerability exploitable with adjacent network access means the vulnerable software is bound to the network stack. The attack is limited at the protocol level to a logically adjacent topology. An attack can be launched from the same shared physical (e.g., Bluetooth or IEEE 802.11) or logical (e.g., local IP subnet) network, or from within a secure or otherwise limited administrative domain.',
        severity: 'medium',
      },
      {
        id: 'L',
        title: 'Local',
        description:
          'A vulnerability exploitable with only local access requires the attacker to have local access to the target system (e.g., keyboard, console), or remotely (e.g., SSH); or rely on User Interaction by another person to perform actions to exploit the vulnerability (e.g., using social engineering techniques to trick a legitimate user into opening a malicious document).',
        severity: 'low',
      },
      {
        id: 'P',
        title: 'Physical',
        description:
          'A vulnerability exploitable with Physical access requires the attacker to have physical access to the vulnerable system or a local (shell) account. Examples of locally exploitable vulnerabilities are peripheral attacks such as Firewire/USB DMA attacks.',
        severity: 'low',
      },
    ],
  },

  AC: {
    title: 'Attack Complexity',
    description:
      'This metric describes the conditions beyond the attacker’s control that must exist in order to exploit the vulnerability. The Base Score is greatest for the least complex attacks.',
    values: [
      {
        id: 'L',
        title: 'Low',
        description:
          'Specialized access conditions or extenuating circumstances do not exist making this easy to exploit',
        severity: 'high',
      },
      {
        id: 'H',
        title: 'High',
        description:
          'Specialized access conditions exist making this harder to exploit',
        severity: 'low',
      },
    ],
  },

  PR: {
    title: 'Privileges Required',
    description:
      'This metric describes the level of privileges an attacker must possess before exploiting the vulnerability. If no privileges are required, the base score is greatest.',
    values: [
      {
        id: 'N',
        title: 'None',
        description: 'The attacker is unauthorized prior to attack.',
        severity: 'high',
      },
      {
        id: 'L',
        title: 'Low',
        description:
          'An attacker with Low privileges has the ability to access only non-sensitive resources.',
        severity: 'medium',
      },
      {
        id: 'H',
        title: 'High',
        description:
          'The attacker requires privileges that provide significant control(e.g., component-wide settings and files) over the vulnerable component.',
        severity: 'low',
      },
    ],
  },

  UI: {
    title: 'User Interaction',
    description:
      'This metric captures the requirement for a human user, other than the attacker, to participate in the successful compromise of the vulnerable component. If no user interaction is required, the base score is greatest.',
    values: [
      {
        id: 'N',
        title: 'None',
        description:
          'The system can be exploited without interaction from any user.',
        severity: 'high',
      },
      {
        id: 'R',
        title: 'Required',
        description:
          'The system can be exploited with user interaction(e.g., installation of an application).',
        severity: 'medium',
      },
    ],
  },

  S: {
    title: 'Scope',
    description:
      'This metric captures whether a vulnerability in one vulnerable component impacts resources in components beyond its security scope. The Base Score is greatest when a scope change occurs.',
    values: [
      {
        id: 'U',
        title: 'Unchanged',
        description:
          'An exploited vulnerability can only affect resources managed by the same security authority. The vulnerable component and the impacted component are either the same, or both are managed by the same security authority.',
        severity: 'low',
      },
      {
        id: 'C',
        title: 'Changed',
        description:
          'An exploited vulnerability can affect resources beyond the security scope managed by the security authority of the vulnerable component. The vulnerable component and the impacted component are different and managed by different security authorities.',
        severity: 'high',
      },
    ],
  },

  C: {
    title: 'Confidentiality Impact',
    description:
      'This metric measures the impact on confidentiality of a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones. Increased confidentiality impact increases the vulnerability score.',
    values: [
      {
        id: 'H',
        title: 'High',
        description:
          "There is a total loss of confidentiality, resulting in disclosing all resources within the impacted component to the attacker. For example, an attacker steals the administrator's password, or private encryption keys of a web server.",
        severity: 'high',
      },
      {
        id: 'L',
        title: 'Low',
        description:
          'There is some loss of confidentiality. Access to some restricted information is obtained, but the attacker does not have control over what information is obtained, or the amount or kind of loss is limited. The information disclosure does not cause a direct, serious loss to the impacted component.',
        severity: 'medium',
      },
      {
        id: 'N',
        title: 'None',
        description: 'There is no impact to the confidentiality of the system.',
        severity: 'low',
      },
    ],
  },

  I: {
    title: 'Integrity Impact',
    description:
      'This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and guaranteed veracity of information. The vulnerability Score is greatest when the consequence to the impacted component is highest.',
    values: [
      {
        id: 'H',
        title: 'High',
        description:
          'There is a total compromise of system integrity. There is a complete loss of system protection, resulting in the entire system being compromised. For example, the attacker is able to modify any/all files on the target system',
        severity: 'high',
      },
      {
        id: 'L',
        title: 'Low',
        description:
          'Modification of some system files or information is possible, but the attacker does not have control over what can be modified, or the scope of what the attacker can affect is limited. For example, system or application files may be overwritten or modified, but either the attacker has no control over which files are affected or the attacker can modify files within only a limited context or scope.',
        severity: 'medium',
      },
      {
        id: 'N',
        title: 'None',
        description: 'There is no impact to the integrity of the system.',
        severity: 'low',
      },
    ],
  },

  A: {
    title: 'Availability Impact',
    description:
      'This metric measures the impact to availability of a successfully exploited vulnerability. Availability refers to the accessibility of information resources. Attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of a system. Increased availability impact increases the vulnerability score.',
    values: [
      {
        id: 'H',
        title: 'High',
        description:
          'There is a total shutdown of the affected resource. The attacker can render the resource completely unavailable.',
        severity: 'high',
      },
      {
        id: 'L',
        title: 'Low',
        description:
          'There is reduced performance or interruptions in resource availability. An example is a network-based flood attack that permits a limited number of successful connections to an Internet service.',
        severity: 'medium',
      },
      {
        id: 'N',
        title: 'None',
        description: 'There is no impact to the availability of the system.',
        severity: 'low',
      },
    ],
  },

  E: {
    title: 'Exploit Code Maturity',
    description:
      'This metric measures the likelihood of the vulnerability being attacked, and is based on the current state of exploit techniques, code availability or active exploitation.',
    values: [
      {
        id: 'X',
        title: 'Not Defined',
        description:
          'Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Temporal Score.',
        severity: 'high',
      },
      {
        id: 'H',
        title: 'High',
        description:
          'No exploit is required and details are widely available. Exploit code works in every situation, or is actively being delivered via an autonomous agent (such as a worm or virus).',
        severity: 'high',
      },
      {
        id: 'F',
        title: 'Functional',
        description:
          'Functional exploit code is available. The code works in most situations where the vulnerability exists.',
        severity: 'medium',
      },
      {
        id: 'P',
        title: 'Proof-of-Concept',
        description:
          'An attack demonstration is not practical for most systems. The code or technique is not functional in all situations and may require substantial modification by a skilled attacker.',
        severity: 'medium',
      },
      {
        id: 'U',
        title: 'Unproven',
        description:
          'No exploit code is available, or an exploit is theoretical.',
        severity: 'low',
      },
    ],
  },

  RL: {
    title: 'Remediation Level',
    description:
      'A typical vulnerability is unpatched when initially published. Workarounds or hotfixes may offer interim remediation until an official patch or upgrade is issued. The less official and permanent a fix, the higher the vulnerability score.',
    values: [
      {
        id: 'X',
        title: 'Not Defined',
        description:
          'Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Temporal Score.',
        severity: 'high',
      },
      {
        id: 'U',
        title: 'Unavailable',
        description:
          'There is either no solution available or it is impossible to apply.',
        severity: 'high',
      },
      {
        id: 'W',
        title: 'Workaround',
        description:
          'There is an unofficial, non-vendor solution available. Users of the affected technology may create a patch of their own or provide steps to work around or mitigate the vulnerability.',
        severity: 'medium',
      },
      {
        id: 'T',
        title: 'Temporary Fix',
        description:
          'There is an official but temporary fix available. This includes instances where the vendor issues a temporary hotfix, tool, or workaround.',
        severity: 'medium',
      },
      {
        id: 'O',
        title: 'Official Fix',
        description:
          'A complete vendor solution is available. Either the vendor has issued an official patch, or an upgrade is available.',
        severity: 'low',
      },
    ],
  },

  RC: {
    title: 'Report Confidence',
    description:
      'This metric measures the degree of confidence in the existence of the vulnerability and the credibility of known technical details. The urgency of a vulnerability is higher when a vulnerability is known to exist with certainty. ',
    values: [
      {
        id: 'X',
        title: 'Not Defined',
        description:
          'Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Temporal Score.',
        severity: 'high',
      },
      {
        id: 'C',
        title: 'Confirmed',
        description:
          'Detailed reports exist, or functional reproduction is possible (functional exploits may provide this).',
        severity: 'high',
      },
      {
        id: 'R',
        title: 'Reasonable',
        description:
          'Significant details are published, but researchers do not have full confidence in the root cause. The bug is reproducible and at least one impact is able to be verified (proof-of-concept exploits may provide this).',
        severity: 'medium',
      },
      {
        id: 'U',
        title: 'Unknown',
        description:
          'Reporters are uncertain of the true nature of the vulnerability, and there is little confidence in the validity of the reports.',
        severity: 'low',
      },
    ],
  },

  CR: {
    title: 'Confidentiality Requirement',
    description:
      'This metrics enables customization of CVSS score depending on the importance of the affected IT asset to a user’s organization, measured in terms of Confidentiality.',
    values: [
      {
        id: 'X',
        title: 'Not Defined',
        description:
          'Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score.',
        severity: 'high',
      },
      {
        id: 'H',
        title: 'High',
        description:
          'Loss of Confidentiality can have a catastrophic adverse effect on the organization or individuals associated (e.g., employees, customers).',
        severity: 'high',
      },
      {
        id: 'M',
        title: 'Medium',
        description:
          'Loss of Confidentiality can have a serious adverse effect on the organization or individuals associated (e.g., employees, customers).',
        severity: 'medium',
      },
      {
        id: 'L',
        title: 'Low',
        description:
          'Loss of Confidentiality can have only a limited adverse effect on the organization or individuals associated (e.g., employees, customers).',
        severity: 'low',
      },
    ],
  },

  IR: {
    title: 'Integrity Requirement',
    description:
      'This metrics enables customization of CVSS score depending on the importance of the affected IT asset to a user’s organization, measured in terms of Integrity.',
    values: [
      {
        id: 'X',
        title: 'Not Defined',
        description:
          'Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score.',
        severity: 'high',
      },
      {
        id: 'H',
        title: 'High',
        description:
          'Loss of Integrity can have a catastrophic adverse effect on the organization or individuals associated (e.g., employees, customers).',
        severity: 'high',
      },
      {
        id: 'M',
        title: 'Medium',
        description:
          'Loss of Integrity can have a serious adverse effect on the organization or individuals associated (e.g., employees, customers).',
        severity: 'medium',
      },
      {
        id: 'L',
        title: 'Low',
        description:
          'Loss of Integrity can have only a limited adverse effect on the organization or individuals associated (e.g., employees, customers).',
        severity: 'low',
      },
    ],
  },

  AR: {
    title: 'Availability Requirement',
    description:
      'This metrics enables customization of CVSS score depending on the importance of the affected IT asset to a user’s organization, measured in terms of Availability.',
    values: [
      {
        id: 'X',
        title: 'Not Defined',
        description:
          'Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score.',
        severity: 'high',
      },
      {
        id: 'H',
        title: 'High',
        description:
          'Loss of Availability can have a catastrophic adverse effect on the organization or individuals associated (e.g., employees, customers).',
        severity: 'high',
      },
      {
        id: 'M',
        title: 'Medium',
        description:
          'Loss of Availability can have a serious adverse effect on the organization or individuals associated (e.g., employees, customers).',
        severity: 'medium',
      },
      {
        id: 'L',
        title: 'Low',
        description:
          'Loss of Availability can have only a limited adverse effect on the organization or individuals associated (e.g., employees, customers).',
        severity: 'low',
      },
    ],
  },

  MAV: {
    title: 'Modified Attack Vector',
    description:
      'This metrics enables the override of base metrics based on specific characteristics of a user’s environment.',
    values: [
      {
        id: 'X',
        title: 'Not Defined',
        description:
          'Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score.',
        severity: 'high',
      },
      {
        id: 'N',
        title: 'Network',
        description:
          'A vulnerability exploitable with network access means the vulnerable software is bound to the network stack and the attacker does not require local network access or local access.  Such a vulnerability is often termed "remotely exploitable".  An example of a network attack is an RPC buffer overflow.',
        severity: 'high',
      },
      {
        id: 'A',
        title: 'Adjacent Network',
        description:
          'A vulnerability exploitable with adjacent network access requires the attacker to have access to either the broadcast or collision domain of the vulnerable software.  Examples of local networks include local IP subnet, Bluetooth, IEEE 802.11, and local Ethernet segment.',
        severity: 'medium',
      },
      {
        id: 'L',
        title: 'Local',
        description:
          'A vulnerability exploitable with only local access requires the attacker to have local access to the target system (e.g., keyboard, console), or remotely (e.g., SSH); or rely on User Interaction by another person to perform actions to exploit the vulnerability (e.g., using social engineering techniques to trick a legitimate user into opening a malicious document).',
        severity: 'low',
      },
      {
        id: 'P',
        title: 'Physical',
        description:
          'A vulnerability exploitable with Physical access requires the attacker to have physical access to the vulnerable system or a local (shell) account. Examples of locally exploitable vulnerabilities are peripheral attacks such as Firewire/USB DMA attacks.',
        severity: '??',
      },
    ],
  },

  MAC: {
    title: 'Modified Attack Complexity',
    description:
      'This metrics enables the override of base metrics based on specific characteristics of a user’s environment.',
    values: [
      {
        id: 'X',
        title: 'Not Defined',
        description:
          'Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score.',
        severity: 'high',
      },
      {
        id: 'L',
        title: 'Low',
        description:
          'Specialized access conditions or extenuating circumstances do not exist making this easy to exploit',
        severity: 'high',
      },
      {
        id: 'H',
        title: 'High',
        description:
          'Specialized access conditions exist making this harder to exploit',
        severity: 'low',
      },
    ],
  },

  MPR: {
    title: 'Modified Privileges Required',
    description:
      'This metrics enables the override of base metrics based on specific characteristics of a user’s environment.',
    values: [
      {
        id: 'X',
        title: 'Not Defined',
        description:
          'Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score.',
        severity: 'high',
      },
      {
        id: 'N',
        title: 'None',
        description: 'The attacker is unauthorized prior to attack.',
        severity: 'high',
      },
      {
        id: 'L',
        title: 'Low',
        description:
          'An attacker with Low privileges has the ability to access only non-sensitive resources.',
        severity: 'medium',
      },
      {
        id: 'H',
        title: 'High',
        description:
          'The attacker requires privileges that provide significant control(e.g., component-wide settings and files) over the vulnerable component.',
        severity: 'low',
      },
    ],
  },

  MUI: {
    title: 'Modified User Interaction',
    description:
      'This metrics enables the override of base metrics based on specific characteristics of a user’s environment.',
    values: [
      {
        id: 'X',
        title: 'Not Defined',
        description:
          'Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score.',
        severity: 'high',
      },
      {
        id: 'N',
        title: 'None',
        description:
          'The system can be exploited without interaction from any user.',
        severity: 'high',
      },
      {
        id: 'R',
        title: 'Required',
        description:
          'The system can be exploited with user interaction(e.g., installation of an application).',
        severity: 'medium',
      },
    ],
  },

  MS: {
    title: 'Modified Scope',
    description:
      'This metrics enables the override of base metrics based on specific characteristics of a user’s environment.',
    values: [
      {
        id: 'X',
        title: 'Not Defined',
        description:
          'Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score.',
        severity: 'high',
      },
      {
        id: 'U',
        title: 'Unchanged',
        description:
          'An exploited vulnerability can only affect resources managed by the same security authority. The vulnerable component and the impacted component are either the same, or both are managed by the same security authority.',
        severity: 'low',
      },
      {
        id: 'C',
        title: 'Changed',
        description:
          'An exploited vulnerability can affect resources beyond the security scope managed by the security authority of the vulnerable component. The vulnerable component and the impacted component are different and managed by different security authorities.',
        severity: 'high',
      },
    ],
  },

  MC: {
    title: 'Modified Confidentiality Impact',
    description:
      'This metrics enables the override of base metrics based on specific characteristics of a user’s environment.',
    values: [
      {
        id: 'X',
        title: 'Not Defined',
        description:
          'Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score.',
        severity: 'high',
      },
      {
        id: 'H',
        title: 'High',
        description:
          "There is total information disclosure, resulting in all system files being revealed. The attacker is able to read all of the system's data (memory, files, etc.)",
        severity: 'high',
      },
      {
        id: 'L',
        title: 'Low',
        description:
          'There is considerable informational disclosure. Access to some system files is possible, but the attacker does not have control over what is obtained, or the scope of the loss is constrained. An example is a vulnerability that divulges only certain tables in a database.',
        severity: 'medium',
      },
      {
        id: 'N',
        title: 'None',
        description: 'There is no impact to the confidentiality of the system.',
        severity: 'low',
      },
    ],
  },

  MI: {
    title: 'Modified Integrity Impact',
    description:
      'This metrics enables the override of base metrics based on specific characteristics of a user’s environment.',
    values: [
      {
        id: 'X',
        title: 'Not Defined',
        description:
          'Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score.',
        severity: 'high',
      },
      {
        id: 'H',
        title: 'High',
        description:
          'There is a total compromise of system integrity. There is a complete loss of system protection, resulting in the entire system being compromised. The attacker is able to modify any files on the target system',
        severity: 'high',
      },
      {
        id: 'L',
        title: 'Low',
        description:
          'Modification of some system files or information is possible, but the attacker does not have control over what can be modified, or the scope of what the attacker can affect is limited. For example, system or application files may be overwritten or modified, but either the attacker has no control over which files are affected or the attacker can modify files within only a limited context or scope.',
        severity: 'medium',
      },
      {
        id: 'N',
        title: 'None',
        description: 'There is no impact to the integrity of the system.',
        severity: 'low',
      },
    ],
  },

  MA: {
    title: 'Modified Availability Impact',
    description:
      'This metrics enables the override of base metrics based on specific characteristics of a user’s environment.',
    values: [
      {
        id: 'X',
        title: 'Not Defined',
        description:
          'Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score.',
        severity: 'high',
      },
      {
        id: 'H',
        title: 'High',
        description:
          'There is a total shutdown of the affected resource. The attacker can render the resource completely unavailable.',
        severity: 'high',
      },
      {
        id: 'L',
        title: 'Low',
        description:
          'There is reduced performance or interruptions in resource availability. An example is a network-based flood attack that permits a limited number of successful connections to an Internet service.',
        severity: 'medium',
      },
      {
        id: 'N',
        title: 'None',
        description: 'There is no impact to the availability of the system.',
        severity: 'low',
      },
    ],
  },
};

export interface SecurityDetailsMetadataProps {
  vulnerability: VulnerabilityListItem;
}
