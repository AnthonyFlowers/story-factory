import {Entity, model, property} from '@loopback/repository';
@model()
export class Transfer extends Entity {
  @property({type: 'string', id: true}) id: string;
  @property({type: 'string', required: true}) fromAccountId: string;
  @property({type: 'string', required: true}) toAccountId: string;
  @property({type: 'number', required: true}) amount: number;
  @property({type: 'string', required: true, jsonSchema: {enum: ['PENDING','COMPLETED','FAILED']}}) status: string;
  @property({type: 'date'}) createdAt: string;
}
