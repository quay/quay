import { AvatarService } from './avatar.service';
import { Injectable, Inject } from 'ng-metadata/core';


@Injectable(AvatarService.name)
export class AvatarServiceImpl implements AvatarService {

  private cache: {[cacheKey: string]: string} = {};

  constructor(@Inject('Config') private Config: any,
              @Inject('md5') private md5: any) {

  }

  public getAvatar(hash: string, size: number = 16, notFound: string = '404'): string {
    var avatarURL: string;
    switch (this.Config['AVATAR_KIND']) {
      case 'local':
        avatarURL = `/avatar/${hash}?size=${size}`;
        break;

      case 'gravatar':
        avatarURL = `//www.gravatar.com/avatar/${hash}?d=${notFound}&size=${size}`;
        break;
    }

    return avatarURL;
  }

  public computeHash(email: string = '', name: string = ''): string {
    const cacheKey: string = email + ':' + name;

    if (this.cache[cacheKey]) {
      return this.cache[cacheKey];
    }

    var hash: string = this.md5.createHash(email.toString().toLowerCase());
    switch (this.Config['AVATAR_KIND']) {
      case 'local':
        if (name) {
          hash = name[0] + hash;
        } else if (email) {
          hash = email[0] + hash;
        }
        break;
    }

    return this.cache[cacheKey] = hash;
  }
}
