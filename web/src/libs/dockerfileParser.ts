export function getRegistryBaseImage(
  content: string,
  domain: string,
): string | null {
  const baseImage = getBaseImage(content);
  if (!baseImage) {
    return null;
  }

  if (baseImage.indexOf(`${domain}/`) != 0) {
    return null;
  }

  return baseImage.substring(domain.length + 1);
}

function getBaseImage(content: string): string | null {
  const imageAndTag = getBaseImageAndTag(content);
  if (!imageAndTag) {
    return null;
  }

  // Note, we have to handle a few different cases here:
  // 1) someimage
  // 2) someimage:tag
  // 3) host:port/someimage
  // 4) host:port/someimage:tag
  const lastIndex: number = imageAndTag.lastIndexOf(':');
  if (lastIndex == -1) {
    return imageAndTag;
  }

  // Otherwise, check if there is a / in the portion after the split point. If so,
  // then the latter is part of the path (and not a tag).
  const afterColon: string = imageAndTag.substring(lastIndex + 1);
  if (afterColon.indexOf('/') != -1) {
    return imageAndTag;
  }

  return imageAndTag.substring(0, lastIndex);
}

function getBaseImageAndTag(content: string): string | null {
  let baseImageAndTag: string = null;

  const fromIndex: number = content.indexOf('FROM ');
  if (fromIndex != -1) {
    let newlineIndex: number = content.indexOf('\n', fromIndex);
    if (newlineIndex == -1) {
      newlineIndex = content.length;
    }

    baseImageAndTag = content
      .substring(fromIndex + 'FROM '.length, newlineIndex)
      .trim();
  }

  return baseImageAndTag;
}
