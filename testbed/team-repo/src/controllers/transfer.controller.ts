import {get, post, param, requestBody} from '@loopback/rest';
import {Transfer} from '../models/transfer.model';
export class TransferController {
  @post('/transfers')
  async create(@requestBody() body: Omit<Transfer, 'id' | 'status' | 'createdAt'>): Promise<Transfer> {
    // status starts as PENDING; a nightly batch completes it
    throw new Error('not implemented');
  }
  @get('/transfers/{id}')
  async findById(@param.path.string('id') id: string): Promise<Transfer> {
    throw new Error('not implemented');
  }
}
