import {Entity, model, property} from '@loopback/repository';
@model()
export class Account extends Entity {
  @property({type: 'string', id: true}) id: string;
  @property({type: 'string', required: true}) ownerId: string;
  @property({type: 'number', required: true}) balance: number;
  @property({type: 'string', required: true}) currency: string;
}
