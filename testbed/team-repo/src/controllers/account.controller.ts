import {get, param} from '@loopback/rest';
import {Account} from '../models/account.model';
export class AccountController {
  @get('/accounts/{id}')
  async findById(@param.path.string('id') id: string): Promise<Account> {
    throw new Error('not implemented');
  }
}
